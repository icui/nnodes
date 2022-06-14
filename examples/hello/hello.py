def main(node):
    """Entry point of the workflow, which is defined in config.toml."""
    print("Hello World!")

    # add a child node with a function task
    node.add(task_hello)

    # add a child node with a Shell command task
    node.add('echo "Hello from echo!"')

    # add child nodes with property defined
    node.add(task_sunday, day='Sunday')

    # add concurrent child node (child nodes of this child node will be executed concurrently)
    node.add(task_monday, day='Monday', concurrent=True)

    # add a child node with a subdirectory as its workspace
    node.add(task_tuesday, day='Tuesday', cwd='tue')


def task_hello(node):
    """A simple printing function."""
    print('Hello from task_hello!')


def task_sunday(node):
    """A task function demonstrating property inheritance."""
    # add a child node inheriting current properties
    node.add(print_today)

    # add a child node that overwrites a property
    node.add(print_today, day='the day before Monday')


def task_monday(node):
    """A task function demonstrating parallel execution."""
    # print the day immediately
    node.add(print_today)

    # print "morning" after 1s
    node.add(print_morning)

    # print "afternoon" after 2s with MPI
    node.add_mpi('sleep 2 && echo "Good afternoon."', 1)

    # print "evening" after 3s with subprocess
    node.add_mpi('sleep 3 && echo "Good evening."', 1, use_multiprocessing=True)

async def print_morning(node):
    """Wait 1s and print."""
    from asyncio import sleep

    # node that asyncio.sleep is different from time.sleep because it does not block the main process
    await sleep(1)
    print('Good morning.')


def task_tuesday(node):
    """A task function demonstrating directory utility."""
    node.add(print_today)

    # write something in base directory
    node.write(node.day, 'today.txt')

    # add a child node writing in a subdirectory
    node.add('echo "noon" > time.txt', cwd='noon')

def print_today(node):
    print(f'Today is {node.day}.')
