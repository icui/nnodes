
import os
import numpy as np


def write_data(data, outdir):

    # Get dir
    datadir = os.path.join(outdir, 'data')

    file = os.path.join(datadir, "data.npy")
    np.save(file, data)


def write_data_processed(data, outdir):
    # Get dir
    datadir = os.path.join(outdir, 'data')

    file = os.path.join(datadir, "data_processed.npy")
    np.save(file, data)


def read_data(outdir):

    # Get dir
    datadir = os.path.join(outdir, 'data')

    return np.load(file=os.path.join(datadir, "data.npy"))


def read_data_processed(outdir):

    # Get dir
    datadir = os.path.join(outdir, 'data')

    return np.load(file=os.path.join(datadir, "data_processed.npy"))
