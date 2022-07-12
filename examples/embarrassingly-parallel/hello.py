"""

The goal of this workflow is to run 50 jobs, each on a single core in an
embarrasingly parallel fashion; that is, the tasks do not need to communicate.

This can be easily done using the `node.add_mpi()`, where node is the root of
the workflow and we simply add `mpi` jobs to it. It is important to realize that
we aren't truly using MPI, since we will just call the function using a single
core. In SLURM, e.g., this is similar to

``` for i in 1...50 do
    srun -n1 <your-script.sh> &
done ```

The difference here is that nnodes will take care of checking whether the calls
made in the for loop are done or not. 

Should the allocation end before all jobs are done. The job can simply be
resubmitted with no intervention of the user whatsoever. For a sample slurm
script please checkout `slurm.sh` in this directory.

"""

from nnodes import Node
from random import randint


def main(node: Node):
    """Entry point of the workflow, which is defined in config.toml
    as root. Meaning that parameters in the config.toml under root are
    propagated here to node.<parameter>, see, e.g.,

    [root].workflowname -> node.workflowname

    Some of the keywords (such as `task`) have special meaning though, so
    be sure to check whether <parameter> is not occupied.

    """

    # Print welcome message using parameter from config.toml
    print(f"Hello {node.workflowname} World!")

    # Set node to concurrent
    node.concurrent = True

    # Add ten jobs to the asynchrouns job submission
    for i in range(50):

        funccall = (
            f'echo "start job {i: 2d}" $(date)'
            f'&& sleep {randint(1,6)}'
            f'&& echo "end   job {i: 2d}" $(date)'
        )

        node.add_mpi(funccall, 1, name=f'job-{i:02d}', cwd='./jobs')
