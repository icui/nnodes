from __future__ import annotations
from os import path
from sys import stderr
from time import time
from datetime import timedelta
from functools import partial
from importlib import import_module
import asyncio
import typing as tp

from .directory import Directory


def parse_import(path: tp.Iterable[str]) -> tp.Any:
    """Import function from a custom module."""
    if isinstance(path, (list, tuple)):
        target = import_module(path[0])

        for key in path[1:]:
            target = getattr(target, key)
        
        return target
    
    return path

# generic Node type for parent and children
N = tp.TypeVar('N', bound='Node')


class Node(Directory, tp.Generic[N]):
    """A directory with a task."""
    # node task
    task: Task

    # task progress prober
    prober: Prober

    # whether child nodes are executed concurrently
    concurrent: tp.Optional[bool]

    # arguments passed to task (pass Node if args is None)
    args: tp.Optional[tp.Iterable]

    # display name
    _name: tp.Optional[str] = None

    # initial data passed to self.__init__
    _init: dict

    # data modified by self.task
    _data: dict

    # parent node
    _parent: tp.Optional[N]

    # time when task started
    _starttime: tp.Optional[float] = None

    # time when MPI task started
    _dispatchtime: tp.Optional[float] = None

    # time when task ended
    _endtime: tp.Optional[float] = None

    # exception raised from self.task
    _err: tp.Optional[Exception] = None

    # child nodes
    _children: tp.List[N]

    @property
    def name(self) -> str:
        """Node name."""
        if self._name is not None:
            return self._name

        func = self.task
        
        if func:
            # use task name as node name
            if isinstance(func, (list, tuple)):
                return func[1]
            
            if isinstance(func, str):
                return func.split('.')[-1]

            while isinstance(func, partial):
                func = func.func
            
            if hasattr(func, '__name__'):
                return func.__name__.lstrip('_')

        # use directory name as node name
        return path.basename(self.path(abs=True))

    @property
    def parent(self) -> N:
        """Parent node."""
        return tp.cast(N, self._parent)

    @property
    def done(self) -> bool:
        """Main function and child nodes executed successfully."""
        if self._endtime:
            return all(node.done for node in self)

        return False
    
    @property
    def elapsed(self) -> tp.Optional[float]:
        """Total walltime."""
        if self.done:
            delta = self._endtime - (self._dispatchtime or self._starttime) # type: ignore
            delta_ws = tp.cast(tp.List[float], [node.elapsed for node in self])

            if self.concurrent and len(delta_ws) > 1:
                return delta + max(*delta_ws)

            return delta + sum(delta_ws)
    
    def __init__(self, cwd: str, data: dict, parent: tp.Optional[N]):
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
            if key.startswith('_'):
                state[key] = getattr(self, key)
        
        return state
    
    def __setstate__(self, state):
        """Restore from saved state."""
        for key, val in state.items():
            setattr(self, key, val)

    def __getitem__(self, key: int) -> N:
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
                    if self.prober:
                        try:
                            state = self.prober(self)

                            if isinstance(state, float):
                                name += f' ({int(state*100)}%)'
                            
                            else:
                                name += f' ({state})'

                        except:
                            pass
                    
                    if name == self.name:
                        name += ' (running)'
        
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
        root.save()

        try:
            # import task
            task = self.task

            if isinstance(task, (list, tuple)):
                # import function from custom module
                task = parse_import(task)
            
            elif isinstance(task, str):
                task = partial(self.call_async, task)
                self.args = ()

            # print to stdout
            indent = 0
            node = self
            while node.parent is not None:
                indent += 2
                node = node.parent

            print(' ' * indent + self.name)

            # call task function
            args = self.args if self.args is not None else [self]
            if task and (result := task(*args)) and asyncio.iscoroutine(result):
                await result
        
        except Exception as e:
            from traceback import format_exc
            
            self._starttime = None
            self._dispatchtime = None
            self._err = e

            print(format_exc(), file=stderr)

            if err or root.job.debug:
                # job failed twice or job in debug mode
                root.job.aborted = True
            
            else:
                # job failed in its first attempt
                root.job.failed = True
        
        else:
            self._endtime = time()
        
        root.save()
    
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
                await asyncio.gather(*(node.execute() for node in wss))

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

    def add(self, task: Task[tp.Any] = None, /,
        cwd: tp.Optional[str] = None, name: tp.Optional[str] = None, *,
        args: tp.Optional[tp.Union[list, tuple]] = None,
        concurrent: tp.Optional[bool] = None, prober: Prober = None, **data) -> N:
        """Add a child node or a child task."""
        if task is not None:
            if isinstance(task, (list, tuple)):
                assert len(task) == 2

            data['task'] = task
        
        if prober is not None:
            data['prober'] = prober
        
        if concurrent is not None:
            data['concurrent'] = concurrent
        
        if args is not None:
            data['args'] = args

        node = Node(self.path(cwd or '.'), data, self)

        if name is not None:
            node._name = name
        
        elif cwd is not None:
            node._name = cwd
        
        self._children.append(tp.cast(N, node))

        return tp.cast(N, node)
    
    def add_mpi(self, cmd: tp.Union[str, tp.Callable], /,
        nprocs: tp.Optional[tp.Union[int, tp.Callable[[Directory], int]]] = None,
        per_proc: tp.Union[int, tp.Tuple[int, tp.Union[int, float]]] = (1, 0), *,
        name: tp.Optional[str] = None, arg: tp.Any = None, arg_mpi: tp.Optional[list] = None,
        check_output: tp.Optional[tp.Callable[[str], None]] = None,
        cwd: tp.Optional[str] = None, data: tp.Optional[dict] = None):
        """Run MPI task."""
        from .mpiexec import mpiexec, getname

        if nprocs is None:
            from .root import root
            nprocs = root.task_nprocs

        if isinstance(per_proc, int):
            per_proc = (per_proc, per_proc)
        
        if isinstance(per_proc[1], float):
            if not 0 < per_proc[1] < 1:
                raise ValueError('per_proc[1] of type float must be a value between 0 and 1')

            if isinstance(nprocs, int) and nprocs % round(1 / per_proc[1]) != 0:
                raise ValueError('nprocs * per_proc[1] must be an integer')
        
        func = partial(mpiexec, cmd, nprocs, per_proc[0], per_proc[1], name, arg, arg_mpi, check_output)
        node = self.add(func, cwd, name or getname(cmd), **(data or {}))
        
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


# type annotation for a node task function
T = tp.TypeVar('T', bound='Node')
Task = tp.Optional[tp.Union[tp.Callable[[T], tp.Optional[tp.Coroutine]], tp.Tuple[str, str], str]]
Prober = tp.Optional[tp.Callable[[Node], tp.Union[float, str, None]]]
