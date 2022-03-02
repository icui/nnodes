import os
import numpy as np
from .utils import read_pickle, write_pickle

def read_optparams(outdir):

    # Write scaling to metadir
    metadir = os.path.join(outdir, 'meta')

    # Optim
    fname = os.path.join(metadir, 'params.pickle')

    # Return parameter dict
    return read_pickle(fname)


def write_optparams(p: dict, outdir):

    # Write scaling to metadir
    metadir = os.path.join(outdir, 'meta')

    # Optim
    fname = os.path.join(metadir, 'params.pickle')

    # Return parameter dict
    return write_pickle(fname, p)


def write_metadata(X, Y, outdir):

    # Write scaling to metadir
    metadir = os.path.join(outdir, 'meta')

    xfile = os.path.join(metadir, "X.npy")
    yfile = os.path.join(metadir, "Y.npy")
    np.save(xfile, X)
    np.save(yfile, Y)


def read_metadata(outdir):
    # Write scaling to metadir
    metadir = os.path.join(outdir, 'meta')

    xfile = os.path.join(metadir, "X.npy")
    yfile = os.path.join(metadir, "Y.npy")
    X = np.load(xfile)
    Y = np.load(yfile)
    return X, Y
