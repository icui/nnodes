# %%
import os
import sys
from nnodes import Node
from lwsspy.seismo.source import CMTSource
from lwsspy.gcmt3d.ioi.utils import optimdir, prepare_inversion_dir, \
    prepare_simulation_dirs, prepare_model, prepare_stations
from lwsspy.gcmt3d.ioi.forward import update_cmt_synt
from lwsspy.gcmt3d.ioi.kernel import update_cmt_dsdm
from lwsspy.gcmt3d.ioi.processing import process_data, window, wprocess_synt, wprocess_dsdm
from lwsspy.gcmt3d.ioi.model import get_simpars, read_model_names
from lwsspy.gcmt3d.ioi.weighting import compute_weights as compute_weights_func
from lwsspy.gcmt3d.ioi.cost import cost
from lwsspy.gcmt3d.ioi.descent import descent
from lwsspy.gcmt3d.ioi.gradient import gradient
from lwsspy.gcmt3d.ioi.hessian import hessian
from lwsspy.gcmt3d.ioi.linesearch import linesearch as linesearch_func
from lwsspy.gcmt3d.ioi.linesearch import check_optvals
from lwsspy.gcmt3d.ioi.opt import check_done, check_status, update_model, update_mcgh

# %%
eventdir = "/home/lsawade/events"
inputfile = "/home/lsawade/lwsspy/lwsspy.gcmt3d/src/lwsspy/gcmt3d/ioi/input.yml"
processfile = "/home/lsawade/lwsspy/lwsspy.gcmt3d/src/lwsspy/gcmt3d/ioi/process.yml"


# Download the data
# get_data(outdir)

# Nparams = int(read_model(modldir, 0, 0).size)

# %%


def read_events(eventdir):
    events = []
    for eventfile in os.listdir(eventdir):
        events.append(os.path.join(eventdir, eventfile))
    print(events)
    return events


def create_event_dir(cmtfile, inputfile):

    outdir, modldir, metadir, datadir, simudir, ssyndir, sfredir, syntdir, \
        frecdir, costdir, graddir, hessdir, descdir, optdir = \
        optimdir(inputfile, cmtfile)

    prepare_inversion_dir(cmtfile, outdir, inputfile)

    # Prepare model
    prepare_model(outdir)

    # Preparing the simulation directory
    prepare_simulation_dirs(outdir)

    # Prep Stations
    prepare_stations(outdir)

    return outdir


def main(node: Node):
    node.concurrent = True

    for event in read_events(eventdir):
        eventname = CMTSource.from_CMTSOLUTION_file(event).eventname
        out = optimdir(inputfile, event, get_dirs_only=True)
        outdir = out[0]
        node.add(cmtinversion, concurrent=False,
                 outdir=outdir, inputfile=inputfile,
                 event=event, eventname=eventname,
                 log='./logs/' + eventname)


def cmtinversion(node: Node):
    node.write(20 * "=", mode='a')
    node.add(iteration, concurrent=False, iter=0, step=0)


def iteration(node: Node):

    if node.iter == 0 and False:

        # Create the inversion directory/makesure all things are in place
        outdir = create_event_dir(node.event, node.inputfile)

        # Forward and frechet modeling
        # node.add(forward_frechet, concurrent=True)

        # Process the data and the synthetics
        # node.add(process_all, concurrent=True, cwd='./logs')

        # Windowing
        # node.add_mpi(window, 1, (10, 0), arg=(outdir), cwd='./logs')

        # Weighting
        # node.add(compute_weights)

        # Cost, Grad, Hess
        # node.add(compute_cgh, concurrent=True)

    # Get descent direction
    node.add(compute_descent)

    # First set of optimization values only computes the initial q and
    # sets alpha to 1
    node.add(compute_optvals)

    node.add(linesearch, step=1)

    node.add(iteration_check)


def transfer_model(node):
    update_mcgh(node.outdir, node.iter, node.step)


def iteration_check(node):
    if check_done(node.outdir, node.iter, node.step):
        pass
    else:
        node.parent.parent.add(iteration, iter=node.iter+1, step=0)


def compute_weights(node):
    compute_weights_func(node.outdir)


def forward_frechet(node):
    node.add(forward, concurrent=True)
    node.add(frechet, concurrent=True)
    # node.add_mpi(queue_multiprocess_stream, 1, (28, 0), args=(st, ...))


def forward(node):
    # setup
    update_cmt_synt(node.outdir, node.iter, node.step)
    node.add_mpi('bin/xspecfem3D', 6, (1, 1),
                 cwd=os.path.join(node.outdir, 'simu', 'synt'))


def frechet(node):
    # Setup
    update_cmt_dsdm(node.outdir, node.iter, node.step)

    # Process the frechet derivatives
    simpars = get_simpars(node.outdir)
    for _i in simpars:
        node.add_mpi('bin/xspecfem3D', 6, (1, 1),
                     cwd=os.path.join(node.outdir, 'simu', 'dsdm', f'dsdm{_i:05d}'))


def process_all(node):

    node.add_mpi(process_data, 1, (10, 0), arg=(
        node.outdir), name=node.eventname + '_process_data')
    node.add(process_synt, concurrent=True)


def process_synt(node):

    # Process the normal synthetics
    node.add_mpi(wprocess_synt, 1, (10, 0),
                 arg=(node.outdir, node.iter, node.step),
                 name=node.eventname + '_process_synt')

    # Process the frechet derivatives
    NM = len(read_model_names(node.outdir))
    for _i in range(NM):
        print(node.outdir, 'simpar', _i)
        node.add_mpi(wprocess_dsdm, 1, (10, 0),
                     arg=(node.outdir, _i, node.iter, node.step),
                     name=node.eventname + f'_process_dsdm{_i:05d}')


def compute_cgh(node):
    node.add(compute_cost)
    node.add(compute_gradient)
    node.add(compute_hessian)


def compute_cost(node):
    cost(node.outdir, node.iter, node.step)


def compute_gradient(node):
    gradient(node.outdir, node.iter, node.step)


def compute_hessian(node):
    hessian(node.outdir, node.iter, node.step)


def compute_descent(node):
    descent(node.outdir, node.iter, node.step)


def compute_optvals(node):
    linesearch_func(node.outdir, node.iter, node.step)


def linesearch(node):
    node.add(search_step)
    node.add(transfer_model)


def search_step(node):
    node.add(compute_new_model)
    node.add(forward_frechet, concurrent=True, outdir=node.outdir)
    node.add(process_synt, concurrent=True, cwd='./logs')
    node.add(compute_cgh, concurrent=True)
    node.add(compute_descent)
    node.add(compute_optvals)
    node.add(search_check)


def compute_new_model(node):
    update_model(node.outdir, node.iter, node.step)


def search_check(node):
    # Check linesearch result.

    if check_optvals(node.outdir, node.iter, node.step):
        node.parent.parent.add(search_step, step=node.step+1)

    # node.add_mpi(process_data, 1, (10, 0), arg=(outdir))
    # node.add_mpi(wprocess_synt, 1, (10, 0),
    #              arg=(outdir, node.iter, node.step))

    # Window the data so that we can make measurements
    # node.add(window_data, 1, (10, 0), arg=(outdir))

    # node.add(compute_cgh)

    # # Compute descent direction
    # node.add(descent)

    # # Start linesearch
    # node.add(linesearch)

    # # Check whether done or another iteration is added.
    # node.add(iter_check)

    # Process forward
    # node.add_mpi(process_synt, 1, (10, 0), arg=(node.outdir))

    # Process frechet
    # which are the frechet params ?
    # for i in frechet_params:
    #     node.add_mpi(process_dsdm, 1, (10, 0), arg=(node.outdir))

    # Check if cost is ok
    # if node.iter == max_iter:
    #     pass
    # else:
    #     node.parent.parent.add(cmtinversion, iter=node.step+1)
    #     node.parent.parent.add(cmtinversion, iter=node.iter+1)

    # def compute_misfit(node):
    #     pass

    # def compute_cgh(node):
    #     node.add(cost)
    #     node.add(gradient)
    #     node.add(hessian)
