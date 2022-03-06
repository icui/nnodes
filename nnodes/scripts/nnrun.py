#!/usr/bin/env python
from nnodes import root
from os import curdir
from os.path import abspath
from sys import path
from time import time
from datetime import timedelta


def bin():

    # Get Current dir
    cwd = abspath(curdir)
    
    # Append current working directory to system path for the import of the 
    # module that contains the workflow. In most cases, the workflow is part
    # of a package s.t. importing is not an issue. But in the case that it is
    # not we better append the path.
    if cwd not in path:
        path.append(cwd)

    # Run the workflow.
    time_start = time()
    root.run()
    print(f'elapsed: {timedelta(seconds=int(time()-time_start))}')
