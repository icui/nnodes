from __future__ import annotations
import asyncio
import typing as tp
from math import ceil
from time import time
from datetime import timedelta
from fractions import Fraction

from .root import root
from .node import getname, getnargs, parse_import, Task, InsufficientWalltime
from .directory import Directory


# pending task, asyncio.Lock -> (nnodes, priority) (Fraction for MPI tasks, int for multiprocessing tasks)
_pending: tp.Dict[asyncio.Lock, tp.Tuple[Fraction | int, int]] = {}

# running tasks, asyncio.Lock -> nnodes
_running: tp.Dict[asyncio.Lock, Fraction | int] = {}


def _dispatch(lock: asyncio.Lock, nnodes: Fraction | int) -> bool:
    """Execute a task if resource is available."""
    ntotal = root.job.mp_nprocs_max if (
        mp := isinstance(nnodes, int)) else root.job.nnodes
    nrunning = sum(v for v in _running.values() if isinstance(v, int) == mp)

    if nrunning == 0 or nnodes <= ntotal - nrunning:
        _running[lock] = nnodes
        return True

    return False


def splitargs(mpiarg: list | tuple, nprocs: int) -> list:
    """Split arguments to n processes."""
    # assign a chunk of arg_mpi to each processor
    mpiarg = sorted(mpiarg)
    args = []
    chunk = int(ceil(len(mpiarg) / nprocs))

    for i in range(nprocs - 1):
        args.append(mpiarg[i * chunk: (i + 1) * chunk])

    args.append(mpiarg[(nprocs - 1) * chunk:])

    return args


async def mpiexec(cmd: Task,
                  nprocs: int | tp.Callable[[Directory], int], cpus_per_proc: int, gpus_per_proc: int,
                  mps: int | None, fname: str | None, args: list | tuple | None, mpiarg: list | tuple | None,
                  group_mpiarg: bool, check_output: tp.Callable[..., None] | None, use_multiprocessing: bool | None,
                  timeout: tp.Literal['auto'] | float | None, ontimeout: tp.Literal['raise'] | tp.Callable[[], None] | None,
                  priority: int, d: Directory) -> str:
    """Schedule the execution of MPI task."""
    # task queue controller
    lock = asyncio.Lock()

    # error occurred
    err = None

    try:
        # get number of MPI processes
        if callable(nprocs):
            nprocs = nprocs(d)

        # remove unused proceesses
        if mpiarg:
            nprocs = min(len(mpiarg), nprocs)

        # calculate node number
        if use_multiprocessing:
            nnodes = nprocs

        else:
            nnodes = Fraction(nprocs * cpus_per_proc, root.job.cpus_per_node)

            if mps:
                # 1 GPU is shared by <mps> processes
                if nprocs % mps != 0:
                    raise ValueError(
                        f'nprocs must be a multiple of mpi ({nprocs}, {mps})')

                nnodes = max(nnodes, Fraction(nprocs//mps, root.job.gpus_per_node))

            elif gpus_per_proc > 0:
                nnodes = max(nnodes, Fraction(
                    nprocs * gpus_per_proc, root.job.gpus_per_node))

            if not root.job.node_splittable:
                nnodes = Fraction(int(ceil(nnodes)))

        # wait for node resources
        await lock.acquire()

        if not _dispatch(lock, nnodes):
            _pending[lock] = (nnodes, priority)
            await lock.acquire()

        # set dispatchtime for node
        if hasattr(d, '_dispatchtime'):
            setattr(d, '_dispatchtime', time())

        # determine file name for log, stdout and stderr
        if fname is None:
            fname = getname(cmd)

            if fname is None:
                fname = 'mpiexec'

            else:
                fname = 'mpiexec_' + fname

        if d.has(f'{fname}.log'):
            i = 1

            while d.has(f'{fname}#{i}.log'):
                i += 1

            fname = f'{fname}#{i}'

        # import task
        if isinstance(cmd, (list, tuple)):
            task = parse_import(cmd)

        else:
            task = cmd

        if not callable(task):
            args = None
            mpiarg = None

        if callable(task) or use_multiprocessing:
            # save function as pickle to run in parallel
            if args:
                args = list(args)

            if mpiarg:
                mpiarg = splitargs(mpiarg, nprocs)

            cwd = None
            d.rm(f'{fname}.*')
            d.dump((task, args, mpiarg, group_mpiarg), f'{fname}.pickle')
            task = f'python -m "nnodes.mpi" {d.path(fname)}'

        else:
            cwd = d.path()

        # wrap with parallel execution command
        if use_multiprocessing:
            task = f'{task} -mp {nprocs}'

        else:
            task = root.job.mpiexec(
                task, nprocs, cpus_per_proc, gpus_per_proc, mps)

        # write the command actually used
        d.write(f'{task}\n', f'{fname}.log')
        time_start = time()

        # timeout due to insufficient walltime
        walltime_out = False

        # create subprocess to execute task
        with open(d.path(f'{fname}.stdout'), 'w') as f_o, open(d.path(f'{fname}.stderr'), 'w') as f_e:

            # execute in subprocess
            process = await asyncio.create_subprocess_shell(task, cwd=cwd, stdout=f_o, stderr=f_e)

            if timeout == 'auto':
                if root.job.inqueue:
                    timeout = root.job.remaining * 60
                    walltime_out = True

                else:
                    timeout = None

            if timeout:
                try:
                    await asyncio.wait_for(process.communicate(), timeout)

                except asyncio.TimeoutError as e:
                    if walltime_out:
                        raise InsufficientWalltime('Insufficient walltime.')

                    elif ontimeout == 'raise':
                        raise e

                    elif ontimeout:
                        ontimeout()

            else:
                await process.communicate()

        # custom function to resolve output
        if check_output:
            nargs = getnargs(check_output)

            if nargs == 0:
                check_output()

            elif nargs == 1:
                check_output(d.read(f'{fname}.stdout'))

            else:
                check_output(d.read(f'{fname}.stdout'),
                             d.read(f'{fname}.stderr'))

        # write elapsed time
        d.write(
            f'\nelapsed: {timedelta(seconds=int(time()-time_start))}\n', f'{fname}.log', 'a')

        if d.has(f'{fname}.error'):
            raise RuntimeError(d.read(f'{fname}.error'))

        elif process.returncode:
            raise RuntimeError(f'{task}\nexit code: {process.returncode}')

    except Exception as e:
        err = e

    # clear entry
    if lock in _pending:
        del _pending[lock]

    if lock in _running:
        del _running[lock]

    # run next MPI task
    if not isinstance(err, InsufficientWalltime) and len(_pending) > 0:
        # sort entries by their node number and priority, np is (nnodes, priority)
        nnodes_max = max(np[0] for np in _pending.values())
        pendings = sorted(_pending.items(), key=lambda item: item[1][1] * nnodes_max + item[1][0], reverse=True)

        # execute tasks if resource is available
        for lock, np in pendings:
            if _dispatch(lock, np[0]):
                del _pending[lock]
                lock.release()

    if err:
        raise err

    return tp.cast(str, fname)
