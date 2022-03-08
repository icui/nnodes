import os
import numpy as np
from .model import read_model, read_scaling
from .gradient import read_gradient
from .hessian import read_hessian
from .metadata import read_optparams


def damp_gH(m, m0, g, H, damping):

    # Compute model residual
    modelres = m - m0

    # Compute damping factor
    factor = damping * np.trace(H) / m.size

    # Update the Hessian and the gradient
    dH = H + factor * np.diag(np.ones(m.size))
    dg = g + factor * modelres

    return dg, dH

def write_descent(dm, outdir, it, ls=None):

    # Get dir
    descdir = os.path.join(outdir, 'desc')

    if ls is not None:
        fname = f"desc_it{it:05d}_ls{ls:05d}.npy"
    else:
        fname = f"desc_it{it:05d}.npy"
    file = os.path.join(descdir, fname)
    np.save(file, dm)


def read_descent(outdir, it, ls=None):

    # Get dir
    descdir = os.path.join(outdir, 'desc')

    if ls is not None:
        fname = f"desc_it{it:05d}_ls{ls:05d}.npy"
    else:
        fname = f"desc_it{it:05d}.npy"
    file = os.path.join(descdir, fname)
    return np.load(file)


def descent(outdir, it, ls=None):

    print(outdir, it, ls)

    # Read model, gradient, hessian
    m = read_model(outdir, it, ls)
    g = read_gradient(outdir, it, ls)
    H = read_hessian(outdir, it, ls)

    # Read optimization parameters
    optparams = read_optparams(outdir)

    # Get damping
    damping = optparams["damping"]
    
    # Read scaling
    s = read_scaling(outdir)

    # Scaling of the cost function
    g *= s
    H = np.diag(s) @ H @ np.diag(s)

    # Damp the gradient and the Hessian
    if damping > 0.0:
        m0 = read_model(outdir, 0, 0)
        g, H = damp_gH(m, m0, g, H, damping)

    # Get direction
    dm = np.linalg.solve(H, -g)

    # Write direction to file
    write_descent(dm*s, outdir, it, ls)

    print("      d: ", np.array2string(dm, max_line_width=int(1e10)))
