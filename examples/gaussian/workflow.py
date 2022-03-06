import os, sys
from functools import partial
from nnodes import Node
from functions.utils import optimdir, removedir
from functions.make_data import make_data, get_NM
from functions.forward import forward
from functions.kernel import frechet
from functions.cost import cost
from functions.gradient import gradient
from functions.hessian import hessian
from functions.descent import descent
from functions.linesearch import linesearch as get_optvals, check_optvals
from functions.opt import check_done, update_mcgh, update_model


# Important directories
workflowdir = os.path.dirname(os.path.abspath(__file__))
outdir = os.path.join(workflowdir, 'optimizations')

# Adding the location of this script s.t. the functions can be load.
sys.path.append(workflowdir)


def main(node):
    node.concurrent = True

    for _i in range(5):
        node.add(inversion, inv=_i)


# ----------------------------- MAIN NODE -------------------------------------
def inversion(node: Node):

    # Make sure that this function runs sequentially
    node.concurrent = False

    # Add the optimization directory to node, so that all subprocesses 
    # have access to the directory
    node.outdir = os.path.join(outdir, f"inversion{node.inv:02d}")

    # Create inversion directory, data, and metadata
    node.add(prepare_dir)

    # Start iteration
    node.add(iteration, iter=0, step=0)
# -----------------------------------------------------------------------------


# ----------------------------- SUB NODES -------------------------------------
def iteration(node: Node):

    if node.iter == 0:

        # Compute synthetics and its frechet derivatives in parallel
        node.add(all_forward, concurrent=True)

        # Computing the cost the gradient and the Hessian
        node.add(compute_cgh, concurrent=True)

    # Compute descent direction
    node.add(compute_descent)

    # Compute baseline optimization parameters
    node.add(compute_optvals)

    # Initiate linesearch
    node.add(linesearch, step=1)

    # Check whether to continue iteration
    node.add(iteration_check)


# Linesearch main function
def linesearch(node: Node):
    # Run search step
    node.add(search_step)

    # If done with linesearch, transfer model, cost, gradient, hessian to next iter
    # node.add(transfer_mcgh)


# The search step function and the main function that is iterated over.
def search_step(node: Node):

    # Compute new model from previous descent direction
    node.add(compute_new_model)

    # Compute forward synthetics and frechet derivatives using new model
    node.add(all_forward, concurrent=True)

    # Compute cost, gradient, and hessian using new model
    node.add(compute_cgh, concurrent=True)

    # # Compute descent direction
    # node.add(compute_descent)

    # Given the new gradient, compute the new optimization values
    node.add(compute_optvals)

    # Check whether the linesearch has to continue and if yes add step
    node.add(search_check)

# -----------------------------------------------------------------------------


# ----------------------------- AUXILIARY NODES -------------------------------

# --------------------------------------------
# Update model in linesearch
def compute_new_model(node: Node):
    update_model(node.outdir, node.iter, node.step)


# Update model, cost, gradient, hessian in iteration
def transfer_mcgh(node: Node):
    print("Transfer Model", node.iter, node.step)
    update_mcgh(node.outdir, node.iter, node.step)


# --------------------------------------------
# Run all forward simulations
def all_forward(node: Node):
    # Forward modeling
    node.add(compute_forward)

    # Kernel computation
    for _i in range(get_NM(node.outdir)):
        node.add(compute_frechet, param=_i)


def _getname(node: Node):
    """Get mpiexec name for forward and frechet."""
    if node.step is not None:
        return f"_it{node.iter:05d}_ls{node.step:05d}"
    else:
        return f"_it{node.iter:05d}"


# Run forward synthetics
def compute_forward(node: Node):
    forward(node.outdir, node.iter, node.step)
    # node.add(partial(forward, node.outdir, node.iter, node.step), args=(), name='fwd_' + _getname(node))


# Run frechet derivative computation
def compute_frechet(node: Node):
    frechet(node.param, node.outdir, node.iter, node.step)
    # node.add(partial(frechet, node.param, node.outdir, node.iter, node.step), args=(), name='fch_' + _getname(node))


# ----------------------------------
# Compute Cost, Gradient, Hessian concurrently
def compute_cgh(node: Node):
    node.add(compute_cost)
    node.add(compute_gradient)
    node.add(compute_hessian)


# Compute Cost
def compute_cost(node: Node):
    cost(node.outdir, node.iter, node.step)


# Compute Gradient
def compute_gradient(node: Node):
    gradient(node.outdir, node.iter, node.step)


# Compute Hessian
def compute_hessian(node: Node):
    hessian(node.outdir, node.iter, node.step)


# Compute Descent
def compute_descent(node: Node):
    descent(node.outdir, node.iter, node.step)


# ----------------------------------
# Compute linesearch parameters
def compute_optvals(node: Node):
    get_optvals(node.outdir, node.iter, node.step)


# Check whether linesearch success, fail, or step added
def search_check(node: Node):
    print("Linesearch Check", node.iter, node.step)
    flag = check_optvals(node.outdir, node.iter, node.step)
    
    if flag == "FAIL":
        node.parent.parent.parent.step = node.step

    elif flag == "SUCCESS":
        # searchstep.linesearch.iteration.cmtinversion
        # Fix the step in the iteration
        node.parent.parent.parent.step = node.step
        # iteration.cmtinversion
        # If linesearch was successful, transfer model
        node.add(transfer_mcgh)

    elif flag == "ADDSTEP":
        node.parent.parent.add(search_step, step=node.step+1)


# Check whether iteration success, fail, or iteration has to be added
def iteration_check(node):
    print("Iteration Check", node.iter, node.step)
    # Get linesearch output
    flag = check_optvals(node.outdir, node.iter, node.step, status=False)

    if flag == "FAIL":
        pass

    elif flag == "SUCCESS":
        if check_done(node.outdir, node.iter, node.step) is False:
            node.parent.parent.add(
                iteration, iter=node.iter+1, step=0)
       

# ----------------------------------
# Prepare the directory you want to run the optimization in.
def prepare_dir(node: Node):

    # Remove the inversion directory if it doesn't exist:
    if os.path.exists(node.outdir):
        removedir(node.outdir)

    # Create the directory
    optimdir(node.outdir)

    # Create artificial data
    make_data(node.outdir, idx=node.inv)

# -----------------------------------------------------------------------------