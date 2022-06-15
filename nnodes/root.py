import typing as tp
import signal
import asyncio
from time import time

from .node import Node, parse_import

if tp.TYPE_CHECKING:
    from .mpi import MPI
    from .job import Job


class Root(Node):
    """Root node with job configuration."""
    # import path for job scheduler
    #system: tp.List[str]

    # MPI workspace (only available with __main__ from nnodes.mpi)
    _mpi             = None

    # runtime global cache
    _cache       = {}

    # module of job scheduler
    #_job: Job

    # currently being saved
    _saving = False

    # dict from config.toml
    #_config: dict
    
    @property
    def cache(self)        :
        return self._cache

    @property
    def job(self)       :
        return self._job
    
    @property
    def mpi(self)       :
        return tp.cast('MPI', self._mpi)
    
    def init(self, mpidir             = None):
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
        self._job = parse_import(self._init['_job']['system'])(self._init['_job'], self._init['_jobstat'])

    async def execute(self):
        """Execute main task."""
        self.init()

        # reset execution state
        self.job.paused = False
        self.job.failed = False
        self.job.aborted = False

        # requeue before job gets killed
        if self.job.inqueue:
            signal.signal(signal.SIGALRM, self._signal)
            signal.alarm(int(self.job.remaining * 60))

        asyncio.create_task(self._ping())
        await super().execute()

        # requeue job if the following conditions are satisfied:
        # 1. job is allocated from job scheduler (can be requeued)
        # 2. any task failed
        # 3. no task failed twice in a row
        # 4. job is not in debug mode
        # 5. job is not already being requeued (due to insufficient walltime)
        if self.job.inqueue and self.job.failed and not self.job.aborted\
            and not self.job.debug and not self.job.paused and self.job.auto_requeue != False:
            self.job.requeue()
    
    def save(self):
        """Save state from event loop."""
        if self.job._signaled:
            # job is being requeued
            return

        if self.mpi:
            # root can only be saved from main process
            raise RuntimeError('cannot save root from MPI process')
        
        self._init['_ping'] = time()
        self.dump(self.__getstate__(), '_root.pickle')
        self.mv('_root.pickle', 'root.pickle')
    
    async def _ping(self):
        """Periodically save to root.pickle."""
        await asyncio.sleep(60)

        if not self.done:
            self.save()
            asyncio.create_task(self._ping())

    def _signal(self, *_):
        """Requeue due to insufficient time."""
        if self.inqueue and not self.job.aborted:
            self.job.paused = True
            self.save()
            self.job._signaled = True
            self.job.requeue()


# create root node
root = Root('.', {}, None)
