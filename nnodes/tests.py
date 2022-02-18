import asyncio


def test(node):
    node.add(test_serial)
    node.add(test_concurrent, concurrent=True)
    node.add(test_mpi, cwd='test_mpi', concurrent=True)


def test_serial(node):
    """Example task: print anything."""
    # approach 1: add function directly
    node.add(test_serial_print, out='    > test 1')

    # approach 2: add function with arguments
    node.add(print, args=('    > test 2',))

    # approach 3: shell command
    node.add('echo "    > test 3"', name="echo")

    # approach 4: import path of function
    node.add(('nnodes.tests', 'test_serial_print'), out='    > test 4')


def test_serial_print(node):
    print(node.out)


def test_concurrent(node):
    """Run two tasks concurrently."""
    node.add(test_concurrent1, delay=2)
    node.add(test_concurrent2, delay=1)


async def test_concurrent1(node):
    await asyncio.sleep(node.delay)
    print('    > test 6')


async def test_concurrent2(node):
    await asyncio.sleep(node.delay)
    print('    > test 5')


def test_mpi(node):
    """Test MPI calls."""
    # approach 1: shell command
    node.add_mpi('echo "test mpi 1"', 4)

    # approach 2: function (only config.toml is loaded in MPI processes, not root.pickle)
    node.add_mpi(test_mpi_print, 4, arg='test mpi 2')

    # approach 3: function process-dependent arguments and default number of MPI processes
    node.add_mpi(test_mpi_write, arg_mpi=list(range(100)))


def test_mpi_print(arg):
    print(arg)


def test_mpi_write(arg):
    from nnodes import root
    import numpy as np

    root.mpi.mpidump(np.array(arg))
