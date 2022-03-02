import os
import numpy as np
from .model import read_model, write_model
from .cost import read_cost, write_cost
from .descent import read_descent
from .gradient import read_gradient, write_gradient
from .hessian import read_hessian, write_hessian
from .linesearch import read_optvals
from .log import write_status
from .metadata import read_optparams


def update_model(outdir, it, ls):

    # Read model, descent direction, and optvals (alpha)
    m = read_model(outdir, it, ls-1)
    dm = read_descent(outdir, it, 0)
    _, _, _, alpha, _, _, _ = read_optvals(outdir, it, ls-1)

    # Compute new model
    m_new = m + alpha * dm

    # Write new model
    write_model(m_new, outdir, it, ls)

    print("      m: ", np.array2string(m_new, max_line_width=int(1e10)))


def update_mcgh(outdir, it, ls):

    # Read all relevant data
    m = read_model(outdir, it, ls)
    c = read_cost(outdir, it, ls)
    g = read_gradient(outdir, it, ls)
    h = read_hessian(outdir, it, ls)

    # Write for the first iteration and 0 ls
    write_model(m, outdir, it + 1, 0)
    write_cost(c, outdir, it + 1, 0)
    write_gradient(g, outdir, it + 1, 0)
    write_hessian(h, outdir, it + 1, 0)


def check_status(outdir):
    fname = "STATUS.txt"
    file = os.path.join(outdir, fname)

    with open(file, "r") as f:
        message = f.read()

    print("    STATUS:", message)

    if "FAIL" in message:
        return False
    else:
        return True


def check_done(outdir, it, ls):

    # Read cost
    cost_init = read_cost(outdir, 0, 0)
    cost_old = read_cost(outdir, it, 0)
    cost = read_cost(outdir, it+1, 0)

    # Read optimizaiton parameters
    optparams = read_optparams(outdir)

    # Get parameters
    stopping_criterion=optparams["stopping_criterion"]
    stopping_criterion_model=optparams["stopping_criterion_model"]
    stopping_criterion_cost_change=optparams["stopping_criterion_cost_change"]

    # Read necessary vals
    _, _, _, alpha, _, _, _ = read_optvals(outdir, it, ls)
    model = read_model(outdir, it, ls)
    model_prev = read_model(outdir, it, ls-1)

    # Init Status flag
    STATUS = False

    if (np.abs(cost - cost_old)/cost_init < stopping_criterion_cost_change):
        message = "FINISHED: Cost function not decreasing enough to justify iteration."
        write_status(outdir, message)
        STATUS = True
    elif (cost/cost_init < stopping_criterion):
        message = "FINISHED: Optimization algorithm has converged."
        write_status(outdir, message)
        STATUS = True
    elif np.sum(model - model_prev)**2/np.sum(model_prev**2) \
            < stopping_criterion_model:
        message = "FINISHED: Model is not updating enough anymore."
        write_status(outdir, message)
        STATUS = True

    return STATUS
