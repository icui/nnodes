from __future__ import annotations
import typing as tp
import asyncio
from os import path
from sys import argv, stderr
from traceback import format_exc
from functools import partial

from .root import root, Node

if tp.TYPE_CHECKING:
    from mpi4py.MPI import Intracomm


class MPI(Node):
    """Node for current MPI workspace."""
    # Index of current MPI process
    rank: int

    # Total number of MPI processes
    size: int

    # MPI Comm World
    comm: Intracomm


def _call(size: int, idx: int):
    mpidir = path.dirname(argv[1]) or '.'
    root.init(mpidir=mpidir)

    if size == 0:
        # use mpi
        from mpi4py.MPI import COMM_WORLD as comm

        root.mpi.comm = comm
        root.mpi.rank = comm.Get_rank()
        root.mpi.size = comm.Get_size()

    else:
        # use multiprocessing
        root.mpi.rank = idx
        root.mpi.size = size
    
    # saved function and arguments from main process
    (func, args, mpiarg, group_mpiarg) = root.load(f'{argv[1]}.pickle')
    

    # call target function
    if callable(func):
        args_all = []
    
        if mpiarg:
            if group_mpiarg:
                # pass mpiarg as a list
                args_all.append([mpiarg[root.mpi.rank]])
            
            else:
                # pass mpiarg as individual args
                for arg in mpiarg[root.mpi.rank]:
                    args_all.append([arg])
            
        else:
            args_all.append([])
        
        for a in args_all:
            if args is not None:
                a += args

            if asyncio.iscoroutine(result := func(*a)):
                asyncio.run(result)
    
    else:
        from subprocess import check_call
        check_call(func, shell=True, cwd=mpidir)


if __name__ == '__main__':
    try:
        if len(argv) > 3 and argv[2] == '-mp':
            # use multiprocessing
            np = int(argv[3])

            if np == 1:
                _call(np, 0)
            
            else:
                from multiprocessing import Pool

                with Pool(processes=np) as pool:
                    pool.map(partial(_call, np), range(np))
        
        else:
            # use mpi
            _call(0, 0)
    
    except Exception:
        err = format_exc()
        print(err, file=stderr)
        root.write(err, f'{argv[1]}.error', 'a')
