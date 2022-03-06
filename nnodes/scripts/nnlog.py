#!/usr/bin/env python
from sys import argv
from nnodes import root


def bin():
    root.init()
    print(root.stat(len(argv) > 1))
