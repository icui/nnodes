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
    node.add(('workflow', 'test_serial_print'), out='    > test 4')


def test_serial_print(node):
    print(node.out)


def test_concurrent(node):
    """Run two tasks concurrently."""
    node.add('sleep 3 && echo "    > test 7"', name='test_concurrent3')
    node.add(test_concurrent1, delay=2)
    node.add(test_concurrent2, delay=1)


async def test_concurrent1(node):
    await node.call_async(f'sleep {node.delay}')
    print('    > test 6')


async def test_concurrent2(node):
    await asyncio.sleep(node.delay)
    print('    > test 5')


def test_mpi(node):
    """Test MPI calls."""
    # approach 1: shell command
    node.add_mpi('echo "test mpi 1"', 4)

    # approach 2: function (only config.toml is loaded in MPI processes, not root.pickle)
    node.add_mpi(test_mpi_print, 4, arg='test mpi 2', name='test_mpi_print1')
    node.add_mpi(test_mpi_print, arg='test mpi 3', name='test_mpi_print2')

    # use multiprocessing
    node.add_mpi(test_mpi_print, arg='test mpi 4', name='test_mpi_print3', use_multiprocessing=True)

    # approach 3: function process-dependent arguments and default number of MPI processes
    node.add_mpi(test_mpi_write, arg_mpi=list(range(100)))

    # test MPI timeout
    node.add_mpi(test_mpi_timeout, timeout=3, ontimeout=test_mpi_ontimeout)


async def test_mpi_timeout():
    await asyncio.sleep(60)


def test_mpi_ontimeout():
    print('    > test 8')


def test_mpi_print(arg):
    print(arg)


def test_mpi_write(arg):
    from nnodes import root
    import numpy as np

    root.mpi.mpidump(np.array(arg))
