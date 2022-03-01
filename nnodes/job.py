import typing as tp
from abc import ABC, abstractmethod
from os import path, environ
from subprocess import check_call


class Job(ABC):
    """Base class for clusters."""
    # job name
    name: tp.Optional[str] = None

    # number of nodes to request
    nnodes: int

    # account to submit the job
    account: tp.Optional[str] = None

    # amount of walltime to request
    walltime: float

    # submit to debug queue and do not requeue if job fails
    debug: bool = False

    # avoid calling new MPI tasks if remaining walltime is less than certain minutes
    gap: float = 0.0

    # number of CPUs per node (if is None, the value must exist in config.toml)
    cpus_per_node: int

    # number of GPUs per node (if is None, the value must exist in config.toml)
    gpus_per_node: int

    @property
    def paused(self):
        """Job paused due to insuffcient time."""
        return self._state[0]
    
    @paused.setter
    def paused(self, key: bool):
        self._state[0] = key

    @property
    def failed(self):
        """Any task failed during execution."""
        return self._state[1]
    
    @failed.setter
    def failed(self, key: bool):
        self._state[1] = key

    @property
    def aborted(self):
        """Any task failed twice during execution."""
        return self._state[2]
    
    @aborted.setter
    def aborted(self, key: bool):
        self._state[2] = key

    # write job submission script to target directory
    @abstractmethod
    def write(self, cmd: str, dst: str): ...

    # resubmit current job
    @abstractmethod
    def requeue(self): ...

    # run a MPI task
    @abstractmethod
    def mpiexec(self, cmd: str, nprocs: int, cpus_per_proc: int = 1, gpus_per_proc: int = 0) -> str: ...

    def __init__(self, job: dict, state: dict):
        # job state (paused, failed, aborted)
        self._state = state

        # set job attributes
        required_keys = ['nnodes', 'walltime', 'cpus_per_node', 'gpus_per_node']

        for key in required_keys:
            if key not in job and not hasattr(self, key):
                raise KeyError(f'required job config `{key}` is missing')

        for key, val in job.items():
            setattr(self, key, val)

    def create(self, dst: tp.Optional[str] = None):
        """Creates a directory as job workspace."""
        from .root import root

        if dst is None:
            # write job script in currect directory
            if root.has('job.bash'):
                raise FileExistsError(f'job.bash already exists')

            dst = '.'
        
        else:
            # write job script in a subdirectory
            if root.has(dst):
                raise FileExistsError(f'{dst} already exists')

        # copy config.toml
        root.dump(root.load('config.toml'), path.join(dst, 'config.toml'))

        # write job submission script
        self.write('python -c "from nnodes import root; root.run()"', dst)


class LSF(Job):
    """LSF-based cluster."""
    def write(self, cmd, dst):
        from .root import root

        # hours and minutes
        hh = int(self.walltime // 60)
        mm = int(self.walltime - hh * 60)

        # job name
        if self.name:
            if dst == '.':
                name = self.name
            
            else:
                name = f'{self.name}_{dst}'
        
        else:
            name = dst

        # job script
        lines = [
            '#!/bin/bash',
            f'#BSUB -J {name}',
            f'#BSUB -W {hh:02d}:{mm:02d}',
            f'#BSUB -nnodes {self.nnodes}',
            f'#BSUB -o lsf.%J.o',
            f'#BSUB -e lsf.%J.e'
        ]

        if self.account:
            lines.append(f'#BSUB -P {self.account}')

        if self.debug:
            lines.append('#BSUB -q debug')

        # add main command
        lines.append(cmd + '\n')

        # write to workspace
        root.writelines(lines, path.join(dst, 'job.bash'))

    def requeue(self):
        """Run current job again."""
        from .root import root

        if environ.get('LSB_INTERACTIVE') != 'Y':
            check_call('brequeue ' + environ['LSB_JOBID'], shell=True)

        else:
            root.job.paused = False

    def mpiexec(self, cmd: str, nprocs: int, cpus_per_proc: int = 1, gpus_per_proc: int = 0):
        """Get the command to call MPI."""
        jsrun = 'jsrun'

        if nprocs == 1:
            # avoid MPI warning in Summit
            jsrun += ' --smpiargs="off"'

        return f'{jsrun} -n {nprocs} -a 1 -c {cpus_per_proc} -g {gpus_per_proc} {cmd}'


class Summit(LSF):
    # number of CPUs per node
    cpus_per_node = 42

    # number of GPUs per node
    gpus_per_node = 6


class Slurm(Job):
    """Slurm-based cluster."""
    def write(self, cmd, dst):
        pass

    def requeue(self):
        pass

    def mpiexec(self, cmd: str, nprocs: int, cpus_per_proc: int = 1, gpus_per_proc: int = 0):
        """Get the command to call MPI."""
        return f'srun -n {nprocs} --cpus-per-task {cpus_per_proc} --gpus-per-task {gpus_per_proc} --ntasks-per-core=1 {cmd}'


class Tiger(Slurm):
    # number of CPUs per node
    cpus_per_node = 28

    # number of GPUs per node
    gpus_per_node = 4


class Traverse(Slurm):
    # number of CPUs per node
    cpus_per_node = 32

    # number of GPUs per node
    gpus_per_node = 4
