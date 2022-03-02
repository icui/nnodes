import os
import numpy as np
from .model import read_model
from .metadata import read_metadata
from .gaussian2d import g


def write_synt(synt, outdir, it, ls=None):

     # Get dir
    syntdir = os.path.join(outdir, 'synt')

    if ls is not None:
        fname = f"synt_it{it:05d}_ls{ls:05d}.npy"
    else:
        fname = f"synt_it{it:05d}.npy"
    file = os.path.join(syntdir, fname)
    np.save(file, synt)


def read_synt(outdir, it, ls=None):

     # Get dir
    syntdir = os.path.join(outdir, 'synt')

    if ls is not None:
        fname = f"synt_it{it:05d}_ls{ls:05d}.npy"
    else:
        fname = f"synt_it{it:05d}.npy"
    file = os.path.join(syntdir, fname)
    return np.load(file)


def forward(outdir, it, ls=None):

    # Read metadata and model
    m = read_model(outdir, it, ls)
    X = read_metadata(outdir)

    # Forward modeling
    synt = g(m, X)

    # Write to disk
    write_synt(synt, outdir, it, ls)
