from __future__ import annotations
from os import path
from sys import stderr
from time import time, sleep
from datetime import timedelta
from functools import partial
from inspect import signature
from importlib import import_module
import asyncio
import typing as tp

from .directory import Directory

if tp.TYPE_CHECKING:
    from .job import Job


class InsufficientWalltime(TimeoutError):
    """Timeout due in insufficient walltime."""


def parse_import(path: tp.List[str] | tp.Tuple[str, ...]) -> tp.Any:
    """Import function from a custom module."""
    if isinstance(path, (list, tuple)):
        target = import_module(path[0])

        for key in path[1:]:
            target = getattr(target, key)
        
        return target
    
    return path


def getnargs(func: tp.Callable) -> int:
    """Get the number of arguments required by a function."""
    return len(signature(func).parameters)


def getname(task: Task) -> str | None:
    """Get default task name."""
    if isinstance(task, (list, tuple)):
        return task[-1]
    
    if isinstance(task, str):
        return task.split(' ')[0].split('/')[-1].split('.')[-1]

    while isinstance(task, partial):
        task = task.func
    
    if hasattr(task, '__name__'):
        return task.__name__.lstrip('_')


# type for a node task
Task = tp.Callable | tp.List[str] | tp.Tuple[str, ...] | str


class Node(Directory):
    """A directory with a task."""
    # node task
    task: Task | None

    # task progress prober
    prober: tp.Callable[..., float | str | None] | None

    # whether child nodes are executed concurrently
    concurrent: bool | None

    # number of times the task is retried
    retry: int | None

    # arguments passed to task (pass Node if args is None)
    args: tp.Iterable | None

    # display name
    _name: str | None = None

    # initial data passed to self.__init__
    _init: dict

    # data modified by self.task
    _data: dict

    # parent node
    _parent: Node | None

    # time when task started
    _starttime: float | None = None

    # time when MPI task started
    _dispatchtime: float | None = None

    # time when task ended
    _endtime: float | None = None

    # task is added from node.add_mpi()
    _is_mpi: bool = False

    # exception raised from self.task
    _err: Exception | None = None

    # child nodes
    _children: tp.List[Node]

    # currently executing async child tasks
    _executing_async: tp.List[tp.Tuple[asyncio.Task, Node]] | None = None

    @property
    def name(self) -> str:
        """Node name."""
        if self._name is not None:
            return self._name

        # use task name
        if self.task and (name := getname(self.task)):
            return name

        # use directory name as node name
        return path.basename(self.path(abs=True))

    @property
    def parent(self) -> Node:
        """Parent node."""
        return tp.cast(Node, self._parent)

    @property
    def done(self) -> bool:
        """Main function and child nodes executed successfully."""
        if self._endtime:
            return all(node.done for node in self)

        return False
    
    @property
    def elapsed(self) -> float | None:
        """Total walltime."""
        if self.done:
            delta = self._endtime - (self._dispatchtime or self._starttime) # type: ignore
            delta_ws = tp.cast(tp.List[float], [node.elapsed for node in self])

            if self.concurrent and len(delta_ws) > 1:
                return delta + max(*delta_ws)

            return delta + sum(delta_ws)
    
    def __init__(self, cwd: str, data: dict, parent: Node | None):
        super().__init__(cwd)
        self._init = data
        self._data = {}
        self._parent = parent
        self._children = []
    
    def __getattr__(self, key: str):
        """Get node data (including parent data)."""
        if key.startswith('_'):
            return object.__getattribute__(self, key)

        if key in self._data:
            return self._data[key]

        if key in self._init:
            return self._init[key]
        
        if key not in tp.get_type_hints(Node) and self._parent:
            return self._parent.__getattr__(key)
        
        return None
    
    def __setattr__(self, key: str, val):
        """Set node data."""
        if key.startswith('_'):
            object.__setattr__(self, key, val)
        
        else:
            self._data[key] = val
    
    def __getstate__(self):
        """Items to be saved when pickled."""
        state = {}
        
        for key in tp.get_type_hints(Node):
            if key.startswith('_') and key != '_executing_async':
                state[key] = getattr(self, key)
        
        return state
    
    def __setstate__(self, state):
        """Restore from saved state."""
        for key, val in state.items():
            setattr(self, key, val)

    def __getitem__(self, key: int) -> Node:
        """Get child node."""
        return self._children[key]

    def __len__(self):
        """Child node number."""
        return len(self._children)
    
    def __iter__(self):
        """Iterate child nodes."""
        return iter(self._children)
    
    def __str__(self):
        """Node name with execution state."""
        from .root import root
        
        name = self.name

        if self._err:
            name += ' (failed)'
        
        elif self._starttime:
            if self._endtime:
                if elapsed := self.elapsed:
                    # task done
                    delta = str(timedelta(seconds=int(round(elapsed))))

                    if delta.startswith('0:'):
                        delta = delta[2:]
                    
                    name += f' ({delta})'

            else:
                # task started but not finished
                if root.job.paused:
                    name += ' (terminated)'
                
                else:
                    if self._is_mpi and self._dispatchtime is None:
                        # MPI task not yet allocated
                        name += ' (pending)'
                    
                    elif self.prober:
                        try:
                            state = self.prober(self) if getnargs(self.prober) > 0 else self.prober()

                            if isinstance(state, float):
                                name += f' ({int(state*100)}%)'
                            
                            else:
                                name += f' ({state})'

                        except:
                            pass
                    
                    if name == self.name:
                        if time() - (root._init.get('_ping') or 0) > 70:
                            # job exited unexpectedly
                            name += ' (not running)'
                        
                        else:
                            # Get current elapsed time
                            celapsed = time() - (self._dispatchtime or self._starttime)
                            dt = str(timedelta(seconds=int(round(celapsed))))

                            # Get attribute string
                            name += f' (running - {dt})'
        
        return name


    def __repr__(self):
        """State of node and child nodes."""
        return self.stat(False)
    
    def run(self):
        """Wrap self.execute with asyncio."""
        asyncio.run(self.execute())
    
    async def execute(self):
        """Execute task and child tasks."""
        await self._exec_task()
        await self._exec_children()
    
    async def _exec_task(self):
        """Execute self.task."""
        from .root import root

        if self._endtime:
            return
        
        self.mkdir()
        
        # save whether previous run failed
        err = self._err

        # backup data and reset state before execution
        self._starttime = time()
        self._dispatchtime = None
        self._endtime = None
        self._err = None
        self._data.clear()
        root.checkpoint()

        retry = 0

        if isinstance(self.retry, int):
            retry = self.retry

        elif isinstance(self.default_retry, int):
            retry = self.default_retry
        
        if retry < 0:
            retry = 0

        for itry in range(retry + 1):
            try:
                # import task
                task = self.task
                args = self.args

                if isinstance(task, (list, tuple)):
                    # import function from custom module
                    task = parse_import(task)
                
                elif isinstance(task, str):
                    task = partial(self.call_async, task)
                    args = ()

                # print to stdout
                indent = 0
                node = self
                while node.parent is not None:
                    indent += 2
                    node = node.parent

                msg = ' ' * indent + self.name
                if itry > 0:
                    msg += f' (retry {itry})'
                print(msg)

                if task:
                    # set default argument
                    if args is None:
                        args = [self] if getnargs(task) > 0 else ()
                    
                    # call task function
                    if (result := task(*args)) and asyncio.iscoroutine(result):
                        await result
            
            except Exception as e:
                from traceback import format_exc

                if isinstance(e, InsufficientWalltime):
                    root._signal()
                    return

                print(format_exc(), file=stderr)
                
                if itry < retry:
                    sleep(1)
                    continue

                self._starttime = None
                self._dispatchtime = None
                self._err = e

                if err or root.job.debug:
                    # job failed twice or job in debug mode
                    root.job.aborted = True
                
                else:
                    # job failed in its first attempt
                    root.job.failed = True
            
            else:
                self._endtime = time()
                break
        
        root.checkpoint()
    
    async def _exec_children(self):
        """Execute self._children."""
        if not self._endtime:
            return

        from .root import root

        # skip executed nodes
        exclude = []

        def get_unfinished():
            wss: tp.List[Node] = []

            for node in self:
                if node not in exclude and not node.done:
                    wss.append(node)

            return wss

        while len(wss := get_unfinished()):
            if self.concurrent:
                # execute nodes concurrently
                exclude += wss
                self._executing_async = []
                await asyncio.gather(*(node.execute() for node in wss))

                # wait for nodes dynamically added during execution
                exclude += [item[1] for item in self._executing_async]
                await asyncio.gather(*(item[0] for item in self._executing_async))
                self._executing_async = None

            else:
                # execute nodes in sequence
                exclude.append(wss[0])
                await wss[0].execute()

            # exit if any error occurs
            if root.job.failed or root.job.aborted:
                break
    
    def update(self, items: dict):
        """Update properties from dict."""
        self._data.update(items)

    def add(self, task: Task | None = None, /,
        cwd: str | None = None, name: str | None = None, *,
        args: list | tuple | None = None, concurrent: bool | None = None,
        prober: tp.Callable[..., float | str | None] | None = None, retry: int | None = None, **data) -> Node:
        """Add a child node with or without a task.

        Args:
            task (Task | None, optional): Task to be executed. Defaults to None.
            cwd (str | None, optional): Working directory of the child node. Defaults to None.
            name (str | None, optional): Name of the child node. If is None, name will be determined by task. Defaults to None.
            retry (int | None, optional): Number of time the task is retried.
            args (list | tuple | None, optional): Arguments passed to task function. Defaults to None.
            concurrent (bool | None, optional): The child node will execute its child nodes concurrently. Defaults to None.
            prober (tp.Callable[..., float  |  str  |  None] | None, optional): Function that probes the execution status of the node.
                If returns a float, the value is the task progress (0 to 1).
                If returns a str, the value is arbitary task status string.
                Defaults to None.

        Returns:
            Node: The child node added.
        """
        if task is not None:
            if isinstance(task, (list, tuple)):
                assert len(task) == 2

            data['task'] = task
        
        if prober is not None:
            data['prober'] = prober
        
        if concurrent is not None:
            data['concurrent'] = concurrent
        
        if retry is not None:
            data['retry'] = retry
        
        if args is not None:
            data['args'] = args

        node = Node(self.path(cwd or '.'), data, self)

        if name is not None:
            node._name = name
        
        elif cwd is not None:
            node._name = cwd
        
        self._children.append(node)

        if isinstance(self._executing_async, list):
            self._executing_async.append((asyncio.create_task(node.execute()), node))

        return node
    
    def add_mpi(self, cmd: Task, /,
        nprocs: int | tp.Callable[[Directory], int] = 1,
        cpus_per_proc: int = 1, gpus_per_proc: int = 0, mps: int | None = None, *,
        name: str | None = None, fname: str | None = None, args: list | tuple | None = None,
        mpiarg: list | tuple | None = None, group_mpiarg: bool = False,
        check_output: tp.Callable[..., None] | None = None, use_multiprocessing: bool | None = None,
        cwd: str | None = None, data: dict | None = None,
        timeout: tp.Literal['auto'] | float | None = 'auto',
        ontimeout: tp.Literal['raise'] | tp.Callable[[], None] | None = 'raise',
        priority: int = 0, exec_args: tp.Dict[tp.Type[Job], str] | None = None, retry: int | None = None) -> Node:
        """Add a child node that executed an MPI task.

        Args:
            cmd (Task): task to be executed
            nprocs (int | tp.Callable[[Directory], int], optional): Number of MPI processes. Defaults to 1.
            cpus_per_proc (int, optional): Number of CPUs in an MPI process. Defaults to 1.
            gpus_per_proc (int, optional): Number of GPUs in an MPI process. Defaults to 0.
            mps (int | None, optional): Number of GPUs in a processes with multi-Process Service (MPS). Defaults to None.
            name (str | None, optional): Task name. Defaults to None.
            fname (str | None, optional): File name of the mpiexec files. Defaults to None.
            args (list | tuple | None, optional): Arguments passed to task. Defaults to None.
            mpiarg (list | tuple | None, optional): Process-specific arguments passed to task.
                If is not None, items in mpiarg will be the first argument passed to each task
                (placed before args). Defaults to None.
            group_mpiarg (bool, optional): Instead of passing each item of mpiarg to a task,
                pass a list of all subitems in mpiarg assigned to it. Defaults to False.
            check_output (tp.Callable[..., None] | None, optional): Optional function after MPI execution.
                Can be used as postprocess script and raise error if the task does not yield desired output.
                Can take 0, 1 or 2 arguments as input.
                If the function takes 1 argument, stdout will be passed.
                If the function takes 2 arguments, stdout and stderr will be passed.
                Defaults to None.
            use_multiprocessing (bool | None, optional): Explicitly determine whether or not to use multiprocessing.
                If is None, multiprocessing will be used based on the job configuration. Defaults to None.
            cwd (str | None, optional): Working directory of the child node. Defaults to None.
            data (dict | None, optional): Keyword arguments set to the child node. Defaults to None.
            timeout (tp.Literal['auto'] | float | None, optional): Abort task if elapsed time > timeout (in minutes).
                If set to 'auto', timeout will be job.walltime - job.gap. Defaults to 'auto'.
            ontimeout (tp.Literal['raise'] | tp.Callable[[], None] | None, optional): Callback when job aborted due to timeout.
                If set to 'raise', an InsufficientWalltime error will be raised. Defaults to 'raise'.
            priority (int, optional): Task priority in mpiexec wait list. Defaults to 0.
            exec_args (tp.Dict[tp.Type[Job], str] | None, optional): Cluster-specific arguments to passed to mpiexec.
                This option is intended to be task-dependant, if you want the option to be applied to all MPI tasks, set root.job.exec_args instead.
                Values of the dict are the arguments, and will be ignored if root.job is not a subclass of its key.
                e.g. {Slurm: '--cpu-freq=low', LSF: '--memory_per_rs 200'} means that '--cpu-freq=low' will be passed to Slurm clusters
                and '--memory_per_rs 200' will be passed to LSF clusters. Defaults to None.

        Returns:
            Node: The child node added that executes the MPI task.
        """
        from .root import root
        from .mpiexec import mpiexec

        if use_multiprocessing is None:
            use_multiprocessing = root.job.use_multiprocessing
        
        if mps and gpus_per_proc != 0:
            print('warning: gpus_per_proc is ignored because mps is set')
        
        func = partial(mpiexec, cmd, nprocs, cpus_per_proc, gpus_per_proc, mps, fname or name,
            args, mpiarg, group_mpiarg, check_output, use_multiprocessing, timeout, ontimeout, priority, exec_args)
        node = self.add(func, cwd, name or fname or getname(cmd), retry=retry, **(data or {}))
        node._is_mpi = True
        
        return node
    
    def reset(self):
        """Reset node (including child nodes)."""
        self._starttime = None
        self._dispatchtime = None
        self._endtime = None
        self._err = None
        self._data.clear()
        self._children.clear()
    
    def stat(self, verbose: bool = False):
        """Structure and execution status."""
        stat = str(self)

        if not verbose:
            stat = stat.split(' ')[0]

        def idx(j):
            if self.concurrent:
                return '- '

            return '0' * (len(str(len(self) - 1)) - len(str(j))) + str(j) + ') '
            
        collapsed = False

        for i, node in enumerate(self):
            stat += '\n' + idx(i)

            if not verbose and (node.done or (collapsed and node._starttime is None)):
                stat += str(node)
        
            else:
                collapsed = True
                
                if len(node):
                    stat += '\n  '.join(node.stat(verbose).split('\n'))
                
                else:
                    stat += str(node)
        
        return stat
