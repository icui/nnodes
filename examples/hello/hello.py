def main(node):
    print("Hello World!")
    node.add(task_hello)
    node.add('echo "Hello from echo!"')
    node.add(task_sunday, day='Sunday')
    node.add(task_monday, day='Monday', concurrent=True)
    node.add(task_tuesday, day='Tuesday', cwd='tue')


def task_hello(node):
    print('Hello from task_hello!')


def task_sunday(node):
    node.add(print_today)
    node.add(print_today, day='the day before Monday')


def task_monday(node):
    node.add(print_today)
    node.add(print_morning)
    node.add_mpi('sleep 2 && echo "Good afternoon."', 1)
    node.add_mpi('sleep 3 && echo "Good evening."', 1, use_multiprocessing=True)

async def print_morning(node):
    from asyncio import sleep
    await sleep(1)
    print('Good morning.')


def task_tuesday(node):
    node.add(print_today)
    node.write(node.day, 'today.txt')
    node.add('echo "noon" > time.txt', cwd='noon')

def print_today(node):
    print(f'Today is {node.day}.')
