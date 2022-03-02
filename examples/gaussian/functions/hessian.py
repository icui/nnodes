import os
import numpy as np
from .kernel import read_frechet
from .model import read_model


def write_hessian(H, outdir, it, ls=None):

    # Get dir
    hessdir = os.path.join(outdir, 'hess')

    if ls is not None:
        fname = f"hess_it{it:05d}_ls{ls:05d}.npy"
    else:
        fname = f"hess_it{it:05d}.npy"
    file = os.path.join(hessdir, fname)
    np.save(file, H)


def read_hessian(outdir, it, ls=None):

    # Get dir
    hessdir = os.path.join(outdir, 'hess')

    if ls is not None:
        fname = f"hess_it{it:05d}_ls{ls:05d}.npy"
    else:
        fname = f"hess_it{it:05d}.npy"
    file = os.path.join(hessdir, fname)
    return np.load(file)


def hessian(outdir, it, ls=None):

    # Read model
    m = read_model(outdir, it, ls)

    # Gradient
    H = np.zeros((m.size, m.size))

    # read each Frechet derivative multiple with the residual and
    for _j in range(m.size):
        dsi_dmj = read_frechet(_j, outdir, it, ls).flatten()

        for _k in range(m.size):
            dsi_dmk = read_frechet(_k, outdir, it, ls).flatten()

            H[_j, _k] = 1/dsi_dmj.size * np.sum(dsi_dmj*dsi_dmk)

    # Write gradient to disk
    write_hessian(H, outdir, it, ls)

    # print("    h: ", H)
