import os
import numpy as np
from .model import read_model
from .metadata import read_metadata
from .gaussian2d import dgdm


def write_frechet(frec, param, outdir, it, ls=None):

    # Get dir
    frecdir = os.path.join(outdir, 'frec')

    if ls is not None:
        fname = f"frec{param:05d}_it{it:05d}_ls{ls:05d}.npy"
    else:
        fname = f"frec{param:05d}_it{it:05d}.npy"
    file = os.path.join(frecdir, fname)
    np.save(file, frec)


def read_frechet(param, outdir, it, ls=None):

    # Get dir
    frecdir = os.path.join(outdir, 'frec')

    if ls is not None:
        fname = f"frec{param:05d}_it{it:05d}_ls{ls:05d}.npy"
    else:
        fname = f"frec{param:05d}_it{it:05d}.npy"
    file = os.path.join(frecdir, fname)
    return np.load(file)


def frechet(param: int, outdir, it, ls):

    # Read metadata and model
    m = read_model(outdir, it, ls)
    X = read_metadata(outdir)

    # Forward modeling
    frechet = dgdm(m, X, param)

    # Write Frechet derivative
    write_frechet(frechet, param, outdir, it, ls)
