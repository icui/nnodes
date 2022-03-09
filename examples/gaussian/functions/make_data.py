from asyncore import write
import os
import numpy as np
from copy import copy, deepcopy
from .data import write_data, write_data_processed
from .model import write_model, write_scaling, write_names
from .metadata import write_metadata
from .gaussian2d import g
from .metadata import write_optparams

def get_NM(outdir):
    """Hardcoded, could be part of a parameter file."""
    return 7

def make_data(outdir, idx=0):

    # actual m: amplitude, x0, yo, sigma_x, sigma_y, theta, offset
    mdictsol = dict(
        a=4,
        x0=115,
        y0=90,
        sigma_x=25,
        sigma_y=35,
        theta=0.0,
        c=2
    )
    m_sol = np.array([val for val in mdictsol.values()])

    # Dictionary for the scaling
    scaling_dict = dict(
        a=1,
        x0=25,
        y0=35,
        sigma_x=25,
        sigma_y=35,
        theta=1,
        c=1
    )
    scaling = np.array([val for val in scaling_dict.values()])

    # List of Initial guesses m0: amplitude, x0, yo, sigma_x, sigma_y, theta, offset
    m_init_list = [
        dict(a=3,   x0=100,  y0=95, sigma_x=25, sigma_y=40, theta=0.1, c=1.0),
        dict(a=4,   x0=120, y0=85, sigma_x=30, sigma_y=30, theta=0.1, c=1.5),
        dict(a=5,   x0=105, y0=95, sigma_x=20, sigma_y=40, theta=0.1, c=2.5),
        dict(a=4.5, x0=100, y0=100, sigma_x=30, sigma_y=30, theta=0.1, c=1.75),
        dict(a=2.75, x0=100, y0=100, sigma_x=30, sigma_y=40, theta=0.1, c=1.0)
    ]

    # Grab one guess depening on the idx parameter
    mdict_init = m_init_list[idx]
    
    m_init = np.array([val for val in mdict_init.values()])

    # Optimization dictionary
    optdict = dict(
        damping = 0.001,
        stopping_criterion = 1e-5,
        stopping_criterion_model = 1e-5,
        stopping_criterion_cost_change = 1e-7,
        niter_max = 10,
        nls_max = 5,
        alpha = 1.0,
        perc = 0.1
    )

    # Create tracked model vectors
    m = copy(m_init)
    mdict = deepcopy(mdict_init)
    mnames = [key for key in mdict.keys()]

    # Write model to disk
    mdict = {key: m[_i] for _i, key in enumerate(mdict_init)}

    # Create some data
    x = np.linspace(0, 200, 201)
    y = np.linspace(0, 200, 201)
    X = np.meshgrid(x, y)

    # Create data
    data = g(m_sol, X)

    # Add reproducible noise 
    np.random.seed(1234567)
    data_processed = data + \
        (np.random.normal(loc=0.0, scale=0.5, size=data.shape))

    # Write initial model to iteration 0, linesearch step 0
    write_model(m, outdir, 0, 0)

    # Write scaling of the model
    write_scaling(scaling, outdir)

    # Write the model names
    write_names(mnames, outdir)

    # Metadatadir
    x, y = X
    write_metadata(x, y, outdir)

    write_model

    # Write data
    write_data(data, outdir)
    write_data_processed(data_processed, outdir)

    # Write optimization parameter dict
    write_optparams(optdict, outdir)

