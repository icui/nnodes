from __future__ import annotations
import typing as tp
import signal
import asyncio
from time import time
from threading import Thread

from .node import Node, parse_import

if tp.TYPE_CHECKING:
    from .mpi import MPI
    from .job import Job


# the last time root.save() is called
_last_save = 0

# current background thread performing save operation
_saving_in_thread: Thread | None = None


class Root(Node):
    """Root node with job configuration."""
    # import path for job scheduler
    system: tp.List[str]

    # internal interval of calling self.save(), set to None to disable
    save_interval: int | float | None = None

    # interval of checking if workflow is alive and update root.pickle, set to None to disable
    ping_interval: int | float | None = 60

    # default value of node.retry
    default_retry: int = 0

    # delay before retry running a task
    retry_delay: int | float = 1

    # save to root.pickle using a separete thread
    async_save: bool = True

    # MPI workspace (only available with __main__ from nnodes.mpi)
    _mpi: MPI | None = None

    # runtime global cache
    _cache: dict = {}

    # module of job scheduler
    _job: Job

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
    
    def init(self, /, mpidir: str | None = None):
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
        root.save()

        # requeue job if the following conditions are satisfied:
        # 1. job is allocated from job scheduler (can be requeued)
        # 2. any task failed
        # 3. no task failed twice in a row
        # 4. job is not in debug mode
        # 5. job is not already being requeued (due to insufficient walltime)
        if self.job.inqueue and self.job.failed and not self.job.aborted \
            and not self.job.debug and not self.job.paused and self.job.auto_requeue != False:
            self.job.requeue()
    
    def checkpoint(self):
        """Save with a certain limit on frequency."""
        global _last_save

        if self.save_interval and time() - self.save_interval < _last_save:
            return
        
        _last_save = time()
        self.save(self.async_save)
    
    def save(self, async_save: bool = False):
        """Save state from event loop."""
        if self.job._signaled:
            # job is being requeued
            return

        if self.mpi:
            # root can only be saved from main process
            raise RuntimeError('cannot save root from MPI process')
        
        self._init['_ping'] = time()

        if async_save:
            asyncio.create_task(self._save_with_thread())
        
        else:
            if _saving_in_thread is not None:
                _saving_in_thread.join()

            self._dump()
    
    async def _save_with_thread(self):
        """Save in a separete thread."""
        global _last_save
        global _saving_in_thread

        if _saving_in_thread:
            return

        t = _saving_in_thread = Thread(target=self._dump)
        t.start()

        while t.is_alive():
            await asyncio.sleep(1)
            _last_save = time()
        
        if _saving_in_thread is t:
            _saving_in_thread = None

    def _dump(self):
        self.dump(self.__getstate__(), '_root.pickle')
        self.mv('_root.pickle', 'root.pickle')

    async def _ping(self):
        """Periodically save to root.pickle."""
        if not self.ping_interval:
            return

        await asyncio.sleep(self.ping_interval)

        if not self.done:
            self.checkpoint()
            asyncio.create_task(self._ping())

    def _signal(self, *_):
        """Requeue due to insufficient time."""
        if self.inqueue and not self.job.aborted and not self.job._signaled:
            self.job.paused = True
            self.save()
            self.job._signaled = True
            self.job.requeue()


# create root node
root = Root('.', {}, None)
