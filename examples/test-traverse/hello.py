"""
just a quick test of traverse runs

"""

from nnodes import Node
from random import randint
import datetime

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
    for i in range(6):

        # These jobs should use an entire node each and since we are asking for 2
        # nodes we need to run 3 "rounds"
        node.add_mpi('python ../runmpitest.py', 12, mps=3,  name=f'job-{i:02d}', cwd='./jobs')


        
