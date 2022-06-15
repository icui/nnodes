# Hello World!

In this section, you will create two files: [```config.toml```](https://raw.githubusercontent.com/icui/nnodes/main/examples/hello/config.toml) and [```hello.py```](https://raw.githubusercontent.com/icui/nnodes/main/examples/hello/hello.py). The structure of the workflow is shown below.

![Workflow](../../../doc/source/images/introduction/hello.png)

## Create config.toml
Use ```nnmk``` as mentioned in introduction.

Enter `3` (personal computer) in system selection.<br>
Enter ```hello``` when prompt ```module containing the main task```.<br>
Enter ```main``` when prompt ```function name of the main task```.

## Print "Hello World!"
We have chose function ```main``` in ```hello.py``` as our main task. Let's define the function first.
```py
# hello.py
def main(node):
    """Entry point of the workflow, which is defined in config.toml."""
    print("Hello World!")
```
A task function by default accepts its ```Node``` as its only argument. In this case, the ```node``` passed to ```main``` is the top level ```root``` node. After creating the file, enter ```nnrun``` and you will see the output.

## Add child tasks
In a task function, you can add a child node with either a function or a shell command as its task.

Add a child node with a function
```py
def main(node):
    # add a child node with a Python function as its task
    node.add(task_func)

def task_func(node):
    """A child task of the main node, will be executed after main()."""
    print('Hello from func!')
```

Add a child node with a shell command
```py
def main(node):
    # add a child node with a Shell command as its task
    node.add('echo "Hello from echo!"')
```

## Add child tasks with properties
Properties are define in keyword arguments in ```Node.add()```.
```py
def main(node):
    # add child nodes with a Python function as its task, with properties defined
    node.add(print_today, day='Sunday')  # Today is Sunday.
    node.add(print_today, day='Monday')  # Today is Monday.
    node.add(print_today, day='Tuesday')  # Today is Tuesday.

def print_today(node):
    """A task function printing its property."""
    print(f'Today is {node.day}.')
```

Properties will be propagated to child nodes, unless overwritten.

```py
def main(node):
    node.add(print_sunday, day='Sunday')

def task_sunday(node):
    # add a chlid node inheriting its property
    node.add(print_today)  # Today is Sunday.

    # add a chlid node that overwrites its property
    node.add(print_today, day='the day before Monday')  # Today is the day before Monday.
```

## Parallel tasks
You can execute all child tasks concurrently by setting the property ```concurrent```. These tasks should either be [async functions](https://docs.python.org/3/library/asyncio-task.html#awaitables) or background tasks (MPI or background process). The following example contains 3 tasks with execution time 1s, 2s and 3s. But the total execution time is 3s because these tasks are executed in parallel.

Note that ```asyncio.sleep``` is not ```time.sleep```, it terminates the current function but the main thread will continue running, going to the next task directly (print "Good afternoon."). This is also not multithreading, the main process is still single-threaded. To learn more, reference to [asyncio module](https://docs.python.org/3/library/asyncio.html).

```py
node.add(task_monday, day='Monday', concurrent=True)

def task_monday(node):
    # add an async function that lasts 1s
    node.add(print_morning) 

     # add a mpi task with 1 CPU that lasts 2s
    node.add_mpi('sleep 2 && echo "Good afternoon."', 1)

    # add a subprocess that lasts 3s
    node.add_mpi('sleep 3 && echo "Good evening."', use_multiprocessing=True)

async def print_morning(node):
    from asyncio import sleep
    await sleep(1)
    print('Good morning')
```


## Directory utilities
Node offers [file system utilities](https://icui.github.io/nnodes/reference/directory.html) like ```cp```, ```mv```, ```read```, ```write```. By default, child tasks use the same directory as its parent, but can be changed by passing a ```cwd``` parameter.
```py
node.add(task_tuesday, day='Tuesday', cwd='tue')

def task_tuesday(node):
    node.add(print_today)

    # writes today.txt in ./tue
    node.write(node.day, 'today.txt')

    # writes time.txt in ./tue/noon
    node.add('echo "noon" > time.txt', cwd='noon')
```

## Understanding root.pickle
During execution, a ```root.pickle``` file will be generated. You can check its content through command ```nnlog```. To re-run a workflow, you need to delete the ```root.pickle``` file because ```root.pickle``` tells nnodes that the workflow is already finished.

You can also directly modify ```root.pickle```. Assuming you have downloaded the complete [```hello.py```](https://raw.githubusercontent.com/icui/nnodes/main/examples/hello/hello.py) file and already executed it with ```nnrun```, you can re-run specific node through a Python interface.

```py
from nnodes import root

# reads workflow status from root.pickle
root.init()

# reset the status of the first child node of root (task_hello)
root[0].reset()
```

After this, if you enter ```nnrun``` again, only the first task of the root node (which is function ```task_hello```) will be executed.
