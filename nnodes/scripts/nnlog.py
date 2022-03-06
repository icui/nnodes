#!/usr/bin/env python
from os import curdir
from os.path import abspath
from sys import argv, path
from nnodes import root


def bin():

    # Get Current dir
    cwd = abspath(curdir)
    
    # Append current working directory to system path for the import of the 
    # module that contains the workflow. In most cases, the workflow is part
    # of a package s.t. importing is not an issue. But in the case that it is
    # not we better append the path.
    if cwd not in path:
        path.append(cwd)

    # Initialize root
    root.init()

    # If any cmd line args are given a detailed log is printed; otherwise 
    # only the top-level log is printed.
    print(root.stat(len(argv) > 1))
