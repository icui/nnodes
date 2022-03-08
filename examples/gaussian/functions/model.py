import os
import numpy as np


def write_model(m, outdir, it, ls=None):
    """Takes in model vector, modldirectory, iteration and linesearch number
    and write model to modl directory.

    Parameters
    ----------
    m : ndarray
        modelvector
    modldir : str
        model directory
    it : int
        iteration number
    ls : int, optional
        linesearch number
    """
    
    # Get dir
    modldir = os.path.join(outdir, 'modl')

    # Create filename that contains both iteration and linesearch number
    if ls is not None:
        fname = f"m_it{it:05d}_ls{ls:05d}.npy"
    else:
        fname = f"m_it{it:05d}.npy"

    file = os.path.join(modldir, fname)
    np.save(file, m)


def read_model(outdir, it, ls=None):
    """Reads model vector

    Parameters
    ----------
    modldir : str
        model directory
    it : int
        iteration number
    ls : int, optional
        linesearch number

    Returns
    -------
    ndarray
        model vector
    """

    # Get dir
    modldir = os.path.join(outdir, 'modl')

    if ls is not None:
        fname = f"m_it{it:05d}_ls{ls:05d}.npy"
    else:
        fname = f"m_it{it:05d}.npy"
    file = os.path.join(modldir, fname)
    m = np.load(file)
    return m


def write_scaling(s, outdir):

    # Write scaling to metadir
    metadir = os.path.join(outdir, 'meta')
    
    # Create filename that contains both iteration and linesearch number
    file = os.path.join(metadir, "scaling.npy")
    
    np.save(file, s)


def sread_scaling(outdir):

    # Write scaling to metadir
    metadir = os.path.join(outdir, 'meta')
    
    # Create filename that contains both iteration and linesearch number
    file = os.path.join(metadir, "scaling.npy")
    
    # Return the scaling vector
    return np.load(file)

def write_names(mnames, outdir):

    # Write scaling to metadir
    metadir = os.path.join(outdir, 'meta')

    # Create filename that contains both iteration and linesearch number
    file = os.path.join(metadir, "model_names.npy")

    np.save(file, mnames)


def read_names(outdir):

    # Write scaling to metadir
    metadir = os.path.join(outdir, 'meta')

    # Create filename that contains both iteration and linesearch number
    file = os.path.join(metadir, "model_names.npy")

    # Return the scaling vector
    return np.load(file)
