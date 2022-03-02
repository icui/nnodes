import os
import numpy as np
from .data import read_data_processed
from .forward import read_synt


def write_cost(c, outdir, it, ls=None):

    # Get cost dir 
    costdir = os.path.join(outdir, 'cost')

    if ls is not None:
        fname = f"cost_it{it:05d}_ls{ls:05d}.npy"
    else:
        fname = f"cost_it{it:05d}.npy"
    file = os.path.join(costdir, fname)
    np.save(file, c)


def read_cost(outdir, it, ls=None):

    # Get cost dir 
    costdir = os.path.join(outdir, 'cost')

    if ls is not None:
        fname = f"cost_it{it:05d}_ls{ls:05d}.npy"
    else:
        fname = f"cost_it{it:05d}.npy"
    file = os.path.join(costdir, fname)
    return np.load(file)


def cost(outdir, it, ls=None):

    # Compute residual
    data = read_data_processed(outdir)
    synt = read_synt(outdir, it, ls)
    resi = synt.flatten() - data.flatten()

    c = 0.5/resi.size * np.sum((resi)**2)

    write_cost(c, outdir, it, ls)

    print("      c:", np.array2string(c, max_line_width=int(1e10)))
