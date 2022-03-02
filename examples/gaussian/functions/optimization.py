# %%

import os
import shutil
import numpy as np

from copy import copy, deepcopy
import numpy as np
import matplotlib.pyplot as plt

# These are the function that have to be hard-coded
from lwsspy.inversion.io.make_data import make_data
from lwsspy.inversion.io.gaussian2d import g
from lwsspy.inversion.io.data import \
    write_data, write_data_processed
from lwsspy.inversion.io.metadata import write_metadata, read_metadata
from lwsspy.inversion.io.model import read_model, write_model
from lwsspy.inversion.io.forward import forward
from lwsspy.inversion.io.kernel import frechet
from lwsspy.inversion.io.cost import cost
from lwsspy.inversion.io.gradient import gradient
from lwsspy.inversion.io.hessian import hessian
from lwsspy.inversion.io.descent import descent

# These are the functions that are basefunction
from lwsspy.inversion.io.log import clear_log
from lwsspy.inversion.io.linesearch import \
    linesearch, check_optvals
from lwsspy.inversion.io.opt import \
    update_model, update_mcgh, check_done, check_status
from lwsspy.inversion.io.plot import plot_cost, plot_model, plot_hessians

# %%

# Little functions to create and removed


def checkdir(cdir):
    if not os.path.exists(cdir):
        os.makedirs(cdir)


def removedir(cdir):
    shutil.rmtree(cdir)


# Setup directories
def optimdir(outdir):

    # Define the directories
    modldir = os.path.join(outdir, "modl")
    metadir = os.path.join(outdir, "meta")
    datadir = os.path.join(outdir, "data")
    syntdir = os.path.join(outdir, "synt")
    frecdir = os.path.join(outdir, "frec")
    costdir = os.path.join(outdir, "cost")
    graddir = os.path.join(outdir, "grad")
    hessdir = os.path.join(outdir, "hess")
    descdir = os.path.join(outdir, "desc")
    optdir = os.path.join(outdir, "opt")

    # Create directories
    checkdir(modldir)
    checkdir(metadir)
    checkdir(datadir)
    checkdir(syntdir)
    checkdir(frecdir)
    checkdir(costdir)
    checkdir(graddir)
    checkdir(hessdir)
    checkdir(descdir)
    checkdir(optdir)

    return modldir, metadir, datadir, syntdir, frecdir, costdir, graddir, \
        hessdir, descdir, optdir


outdir = "/home/lsawade/optimizationdir"
# problem_module = "/Users/lucassawade/lwsspy/lwsspy/src/lwsspy/inversion/io/problem/__init__.py"

# problem = import_problem(problem_module)
# %%

# Inversion parameters
damping = 0.01
stopping_criterion = 1e-5
stopping_criterion_model = 0.001
stopping_criterion_cost_change = 1e-3
niter_max = 10
nls_max = 10
alpha = 1.0
perc = 0.1
it0 = 0

#  %% Remove and create optimdir

if os.path.exists(outdir):
    removedir(outdir)

modldir, metadir, datadir, syntdir, frecdir, costdir, graddir, \
    hessdir, descdir, optdir = optimdir(outdir)

# %%

# Make data and get first model
make_data(datadir, modldir, metadir, outdir)
Nparams = int(read_model(modldir, 0, 0).size)

# %%
for it in range(it0, niter_max):

    print(f"Iteration: {it:05d}")
    print("----------------")

    # Reset the linesearch iterator
    ls = 0

    if it == 0:

        # Forward modeling
        forward(modldir, metadir, syntdir, it, ls)

        # Kernel computation
        for _i in range(Nparams):
            frechet(_i, modldir, metadir, frecdir, it, ls)

        # Computing the cost the gradient and the Hessian
        cost(datadir, syntdir, costdir, it, ls)
        gradient(
            modldir, graddir, syntdir, datadir, frecdir, it, ls)
        hessian(modldir, hessdir, frecdir, it, ls)

    # Get descent direction
    descent(modldir, graddir, hessdir,
            descdir, outdir, damping, it, ls)

    # First set of optimization values only computes the initial q and
    # sets alpha to 1
    linesearch(optdir, descdir, graddir, costdir, it, ls)

    for ls in range(1, nls_max):

        print(f"  Linesearch: {ls:05d}")
        print("  -----------------")

        # Update the model
        update_model(modldir, descdir, optdir, it, ls - 1)

        # Forward modeling
        forward(modldir, metadir, syntdir, it, ls)

        # Kernel computation
        for _i in range(Nparams):
            frechet(_i, modldir, metadir, frecdir, it, ls)

        # Computing the cost the gradient and the Hessian
        cost(datadir, syntdir, costdir, it, ls)
        gradient(
            modldir, graddir, syntdir, datadir, frecdir, it, ls)
        hessian(modldir, hessdir, frecdir, it, ls)

        # Get descent direction
        descent(modldir, graddir, hessdir,
                descdir, outdir, damping, it, ls)

        # Compute optimization values
        linesearch(optdir, descdir, graddir, costdir, it, ls)

        # Check optimization values
        if not check_optvals(optdir, outdir, costdir, it, ls, nls_max):
            break

    # Check optimization status
    if not check_status(outdir):
        break
    else:
        print("\n-------------------------------\n")

    # Update model
    # If the linesearch is successful reassign the model grad etc for the next
    # iteration. The final iteration of the linesearch is the first grad of the
    # next iteration
    update_mcgh(modldir, costdir, graddir, hessdir, it, ls)

    # With the new model check wether the new cost satisfies the stopping conditions
    if check_done(
            optdir, modldir, costdir, descdir, outdir, it, ls,
            stopping_criterion=stopping_criterion,
            stopping_criterion_model=stopping_criterion_model,
            stopping_criterion_cost_change=stopping_criterion_cost_change):
        break


plot_cost(outdir)
plot_model(outdir)
plot_hessians(outdir)
plt.show(block=True)
