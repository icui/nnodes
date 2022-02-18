from __future__ import annotations
import typing as tp
import signal

from .node import Node, parse_import

if tp.TYPE_CHECKING:
    from .mpi import MPI
    from .job import Job


class Root(Node):
    """Root node with job configuration."""
    # import path for job scheduler
    system: tp.List[str]

    # default number of nodes to run MPI tasks (if task_nnodes is None, task_nprocs must be set)
    task_nnodes: tp.Optional[int]

    # MPI workspace (only available with __main__ from nnodes.mpi)
    _mpi: tp.Optional[MPI] = None

    # runtime global cache
    _cache: dict = {}

    # module of job scheduler
    _job: Job

    # currently being saved
    _saving = False

    # dict from config.toml
    _config: dict
    
    @property
    def cache(self) -> dict:
        return self._cache

    @property
    def job(self) -> Job:
        return self._job
    
    @property
    def mpi(self) -> MPI:
        return tp.cast('MPI', self._mpi)

    @property
    def task_nprocs(self) -> int:
        """Default number of processors to run MPI tasks."""
        if 'task_nprocs' in self._data:
            return self._data['task_nprocs']

        if 'task_nprocs' in self._init:
            return self._init['task_nprocs']

        if self.task_nnodes is None:
            raise KeyError('default number of MPI processes (task_nprocs or task_nnodes) is not set')

        return self.task_nnodes * self.job.cpus_per_node
    
    def init(self, /, mpidir: tp.Optional[str] = None):
        """Restore state."""
        if hasattr(self, '_job'):
            # root already initialized
            return
        
        if mpidir is None and self.has('root.pickle'):
            # restore from save file
            self.__setstate__(self.load('root.pickle'))
        
        elif self.has('config.toml'):
            # load configuration
            config = self.load('config.toml')
            self._init.update(config['root'])
            self._init['_job'] = config['job']
            self._init['_jobstat'] = [False, False, False]

        # create MPI object
        if mpidir:
            from .mpi import MPI
            self._mpi = MPI(mpidir, {}, self)

        # create Job object
        self._job = parse_import(self.system)(self._init['_job'], self._init['_jobstat'])

    async def execute(self):
        """Execute main task."""
        self.init()

        # reset execution state
        self.job.paused = False
        self.job.failed = False
        self.job.aborted = False

        # requeue before job gets killed
        if not self.job.debug:
            signal.signal(signal.SIGALRM, self._signal)
            signal.alarm(int((self.job.walltime - self.job.gap) * 60))

        await super().execute()

        # requeue job if task failed
        if self.job.failed and not self.job.aborted and not self.job.debug and not self.job.paused:
            self.job.paused = True
            self.job.requeue()
    
    def save(self):
        """Save state from event loop."""
        if self.job.paused:
            # job is being requeued
            return

        if self.mpi:
            # root can only be saved from main process
            raise RuntimeError('cannot save root from MPI process')
        
        self.dump(self.__getstate__(), '_root.pickle')
        self.mv('_root.pickle', 'root.pickle')

    def _signal(self, *_):
        """Requeue due to insufficient time."""
        if not self.job.aborted:
            self.save()
            self.job.paused = True
            self.job.requeue()


# create root node
root = Root('.', {}, None)
