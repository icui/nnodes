import typing as tp
import asyncio
from os import path
from sys import argv, stderr
from traceback import format_exc
from mpi4py.MPI import COMM_WORLD as comm

from .root import root, Node


class MPI(Node):
    """Node for current MPI workspace."""
    # Index of current MPI process
    rank: int = comm.Get_rank()

    # Total number of MPI processes
    size: int = comm.Get_size()

    # MPI Comm World
    comm = comm

    # Default file name of current process
    @property
    def pid(self):
        return f'p{"0" * (len(str(self.size - 1)) - len(str(self.rank)))}{self.rank}'
    
    def mpiload(self, src: str = '.'):
        """Read from a MPI directory."""
        if self.has(fname := path.join(src, self.pid + '.npy')):
            return self.load(fname)
        
        return self.load(path.join(src, self.pid + '.pickle'))
    
    def mpidump(self, obj, dst: str = '.'):
        """Save with MPI file name."""
        from numpy import ndarray

        ext = '.npy' if isinstance(obj, ndarray) else '.pickle'
        self.dump(obj, path.join(dst, self.pid + ext), mkdir=False)


if __name__ == '__main__':
    try:
        # saved function and arguments from main process
        (func, arg, arg_mpi) = root.load(f'{argv[1]}.pickle')
        root.init(mpidir=path.dirname(argv[1]) or '.')

        # determine arguments
        args = []

        if arg is not None:
            args.append(arg)

        if arg_mpi is not None:
            args.append(arg_mpi[tp.cast(MPI, root.mpi).rank])

        if asyncio.iscoroutine(result := func(*args)):
            asyncio.run(result)
    
    except Exception:
        err = format_exc()
        print(err, file=stderr)
        root.write(err, f'{argv[1]}.error', 'a')
