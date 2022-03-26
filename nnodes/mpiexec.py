from __future__ import annotations
import asyncio
import typing as tp
from math import ceil
from time import time
from datetime import timedelta
from fractions import Fraction

from .root import root
from .node import getname, getnargs, parse_import, Task
from .directory import Directory


# pending tasks (Fraction for MPI tasks, int for multiprocessing tasks)
_pending: tp.Dict[asyncio.Lock, Fraction | int] = {}

# running tasks (Fraction for MPI tasks, int for multiprocessing tasks)
_running: tp.Dict[asyncio.Lock, Fraction | int] = {}


def _dispatch(lock: asyncio.Lock, nnodes: Fraction | int) -> bool:
    """Execute a task if resource is available."""
    ntotal = root.job.mp_nprocs_max if (mp := isinstance(nnodes, int)) else root.job.nnodes
    nrunning = sum(v for v in _running.values() if isinstance(v, int) == mp)

    if nrunning == 0 or nnodes <= ntotal - nrunning:
        _running[lock] = nnodes
        return True
    
    return False


async def mpiexec(cmd: Task,
    nprocs: int | tp.Callable[[Directory], int], cpus_per_proc: int, gpus_per_proc: int,
    mps: int | None, name: str | None, arg: tp.Any, arg_mpi: list | tuple | None,
    check_output: tp.Callable[..., None] | None, use_multiprocessing: bool | None,
    timeout: tp.Literal['auto'] | float | None, ontimeout: tp.Literal['raise'] | tp.Callable[[], None] | None,
    d: Directory) -> str:
    """Schedule the execution of MPI task"""
    # task queue controller
    lock = asyncio.Lock()

    # error occurred
    err = None
    
    try:
        # get number of MPI processes
        if callable(nprocs):
            nprocs = nprocs(d)

        # remove unused proceesses
        if arg_mpi:
            nprocs = min(len(arg_mpi), nprocs)

        # calculate node number
        if use_multiprocessing:
            nnodes = nprocs
        
        else:
            nnodes = Fraction(nprocs * cpus_per_proc, root.job.cpus_per_node)
            
            if mps:
                # 1 GPU is shared by <mps> processes
                if nprocs % mps != 0:
                    raise ValueError(f'nprocs must be a multiple of mpi ({nprocs}, {mps})')

                nnodes = max(nnodes, Fraction(nprocs, mps))

            elif gpus_per_proc > 0:
                nnodes = max(nnodes, Fraction(nprocs * gpus_per_proc, root.job.gpus_per_node))
            
            if not root.job.node_splittable:
                nnodes = Fraction(int(ceil(nnodes)))

        # wait for node resources
        await lock.acquire()

        if not _dispatch(lock, nnodes):
            _pending[lock] = nnodes
            await lock.acquire()
        
        # set dispatchtime for node
        if hasattr(d, '_dispatchtime'):
            setattr(d, '_dispatchtime', time())

        # determine file name for log, stdout and stderr
        if name is None:
            name = getname(cmd)

            if name is None:
                name = 'mpiexec'
            
            else:
                name = 'mpiexec_' + name
        
        i = 1
        while d.has(f'{name}.log'):
            name = f'{name}#{i}'
            i += 1
        
        
        # import task
        if isinstance(cmd, (list, tuple)):
            task = parse_import(cmd)
        
        else:
            task = cmd
        
        if not callable(task) and (arg is not None or arg_mpi is not None):
            raise NotImplementedError('cannot add arguments to shell command')

        if callable(task) or use_multiprocessing:
            # save function as pickle to run in parallel
            if arg_mpi:
                # assign a chunk of arg_mpi to each processor
                arg_mpi = sorted(arg_mpi)
                args = []
                chunk = int(ceil(len(arg_mpi) / nprocs))
                
                # adjust number of processors
                if nprocs * chunk > len(arg_mpi):
                    nprocs -= (nprocs * chunk - len(arg_mpi)) // chunk

                for i in range(nprocs - 1):
                    args.append(arg_mpi[i * chunk: (i + 1) * chunk])
                
                args.append(arg_mpi[(nprocs - 1) * chunk:])
            
            else:
                args = None

            cwd = None
            d.rm(f'{name}.*')
            d.dump((task, arg, args), f'{name}.pickle')
            task = f'python -m "nnodes.mpi" {d.path(name)}'
        
        else:
            cwd = d.path()
        
        # wrap with parallel execution command
        if use_multiprocessing:
            task = f'{task} -mp {nprocs}'
        
        else:
            task = root.job.mpiexec(task, nprocs, cpus_per_proc, gpus_per_proc, mps)
        
        # write the command actually used
        d.write(f'{task}\n', f'{name}.log')
        time_start = time()
        
        # create subprocess to execute task
        with open(d.path(f'{name}.stdout'), 'w') as f_o, open(d.path(f'{name}.stderr'), 'w') as f_e:

            # execute in subprocess
            process = await asyncio.create_subprocess_shell(task, cwd=cwd, stdout=f_o, stderr=f_e)
            
            if timeout == 'auto':
                if root.job.inqueue:
                    timeout = root.job.remaining * 60
                
                else:
                    timeout = None

            if timeout:
                try:
                    await asyncio.wait_for(process.communicate(), timeout)
                
                except asyncio.TimeoutError as e:
                    if ontimeout == 'raise':
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
                check_output(d.read(f'{name}.stdout'))
            
            else:
                check_output(d.read(f'{name}.stdout'), d.read(f'{name}.stderr'))

        # write elapsed time
        d.write(f'\nelapsed: {timedelta(seconds=int(time()-time_start))}\n', f'{name}.log', 'a')

        if d.has(f'{name}.error'):
            raise RuntimeError(d.read(f'{name}.error'))

        elif process.returncode:
            raise RuntimeError(f'{task}\nexit code: {process.returncode}')
    
    except Exception as e:
        err = e
    
    # clear entry
    if lock in _pending:
        del _pending[lock]
    
    if lock in _running:
        del _running[lock]
    
    # sort entries by their node number
    pendings = sorted(_pending.items(), key=lambda item: item[1], reverse=True)

    # execute tasks if resource is available
    for lock, nnodes in pendings:
        if _dispatch(lock, nnodes):
            del _pending[lock]
            lock.release()

    if err:
        raise err

    return tp.cast(str, name)
