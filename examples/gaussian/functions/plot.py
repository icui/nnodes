import sys
from typing import Iterable
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import InsetPosition
import numpy as np
import os
from matplotlib.ticker import MaxNLocator

from .model import read_scaling, read_names

def plot_cost(outdir):

    # Cost dir
    costdir = os.path.join(outdir, 'cost')

    clist = []
    for _cfile in sorted(os.listdir(costdir)):
        if "_ls00000.npy" in _cfile:
            clist.append(np.load(os.path.join(costdir, _cfile)))

    plt.figure()
    ax = plt.axes()
    plt.plot(np.log10(clist/clist[0]))
    plt.xlabel("Iteration #")
    plt.ylabel("$\\log_{10}\\,C/C_0$")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.savefig("cost_single.png", dpi=150)


def plot_hessians(outdir):
    hessdir = os.path.join(outdir, 'hess')
    s = read_scaling(outdir)
    mnames = read_names(outdir)

    mlist = []
    for _mfile in sorted(os.listdir(hessdir)):
        if "_ls00000.npy" in _mfile:
            mlist.append(np.load(os.path.join(hessdir, _mfile)))

    N = len(mlist)
    n = int(np.ceil(np.sqrt(N)))

    # Get number of rows and colums
    ncols = n
    if (N/n) < (n-1):
        nrows = n - 1
    else:
        nrows = n

    fig, axes = plt.subplots(
        nrows, ncols, figsize=(2*ncols + 1.0, nrows*2+1.0))
    plt.subplots_adjust(hspace=0.4)

    counter = 0
    for _i in range(nrows):

        for _j in range(ncols):

            if nrows == 1:
                ax = axes[_j]
            else:
                ax = axes[_i][_j]

            if len(mlist) > counter:
                im = ax.imshow(
                    np.diag(s) @ mlist[counter] @ np.diag(s))
                ax.axis('equal')

                # Show model names on the left for first plot only
                if counter==0:
                    ax.tick_params(which='both', top=False,
                        bottom=False, left=True, right=False, labelleft=True)
                    ax.set_yticks([l for l in range(len(mnames))])
                    ax.set_yticklabels(mnames)
                    ax.set_xticks([])
                # Otherwise remove everything except spines
                else:
                    ax.tick_params(
                        which='both', top=False,
                        bottom=False, left=False, right=False,
                        labelleft=False, labelbottom=False)
                ax.set_title(f"{counter}")
                cax = axes_from_axes(
                    ax, 99080+counter, [0., -.05, 1.0, .05])
                plt.colorbar(im, cax=cax, orientation='horizontal')
            else:
                ax.axis('off')
            counter += 1

    plt.savefig("hessians.png", dpi=150)


def plot_model(optdir):

    modldir = os.path.join(optdir, 'modl')
    mlist = []
    for _mfile in sorted(os.listdir(modldir)):
        if "_ls00000.npy" in _mfile:
            mlist.append(np.load(os.path.join(modldir, _mfile)))

    mlist = np.array(mlist)
    plt.figure()
    ax = plt.axes()
    plt.plot(mlist/mlist[0])
    plt.xlabel("Iteration #")
    plt.ylabel("$M/M_0$")
    # ax.set_yscale('log')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend([_i for _i in range(mlist[0].size)])

    plt.savefig("models_single.png", dpi=150)


def plot_all_costs(optimdir):

    costs = []
    maxs = []
    for _outdir in sorted(os.listdir(optimdir)):
        
        # Cost dir
        costdir = os.path.join(optimdir, _outdir, 'cost')

        # Get costs
        clist = []
        for _cfile in sorted(os.listdir(costdir)):
            if "_ls00000.npy" in _cfile:
                clist.append(float(np.load(os.path.join(costdir, _cfile))))
        
        costs.append(clist)
        maxs.append(np.max(clist))
    
    # Get overall max
    cmax = np.max(maxs)
    
    # Create Figure
    plt.figure()
    ax = plt.axes()

    # Plot cost lines
    for _i, _clist in enumerate(costs):
        plt.plot(np.log10(_clist/cmax), label=f"Inv{_i:02d}")

    plt.xlabel("Iteration #")
    plt.ylabel("$\\log_{10}\\,C/C_0$")
    plt.legend()
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.savefig('costs.png', format='png', dpi=150)


def plot_all_models(optimdir):
   
    # Get all the inversions models
    inversions = []
    for _outdir in sorted(os.listdir(optimdir)):

        # Get dirs
        outdir = os.path.join(optimdir, _outdir)
        modldir = os.path.join(outdir, 'modl')

        # Get the scaling and the model directory
        mnames = read_names(outdir)
        s = read_scaling(outdir)
        
        mlist = []
        for _mfile in sorted(os.listdir(modldir)):

            if "_ls00000.npy" in _mfile:
                mlist.append((np.load(os.path.join(modldir, _mfile))/s).tolist())
        mlist = np.array(mlist)
        inversions.append(mlist)

    # Get number of inversions
    Ninv = len(inversions)

    # Get number of model parameters
    N = len(s)
    n = int(np.ceil(np.sqrt(N)))


    # Get number of rows and colums
    ncols = n
    
    if (N/n) < (n-1):
        nrows = n - 1
    else:
        nrows = n
    
    # Add custom space for legend outside
    factor = 1.0 if (nrows*ncols) == N else 0.0 
    right = 0.8 if (nrows*ncols) == N else None

    # Create subplots
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(2*ncols + 1.0 + factor, nrows*2+1.0))
    
    # Adjust subplots
    plt.subplots_adjust(hspace=0.4, right=right, wspace=0.3)

    # Create space for common x- and y-labels
    fig.add_subplot(111, frameon=False)
    plt.tick_params(
        labelcolor='none', which='both', top=False,
        bottom=False, left=False, right=False)
    # Add common x- and y-labels
    plt.xlabel("Iteration #")
    plt.ylabel("$M/M_0$")
    

    counter = 0
    for _i in range(nrows):
        for _j in range(ncols):

            if nrows == 1:
                ax = axes[_j]
            else:
                ax = axes[_i][_j]

            if N > counter:
                for _k in range(Ninv):
                    ax.plot(inversions[_k][:, counter], label=f"Inv{_k:02d}")
                    # ax.axis('equal')
                    # ax.axis('off')
                    ax.set_title(f"{mnames[counter]}")
                    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            else:
                ax.axis('off')

            if N-1 == counter:
                ax.legend(loc=2, bbox_to_anchor=(1.0, 1.0), fancybox=False)

            
            counter += 1

    plt.savefig('models.png', format='png', dpi=150)




def axes_from_axes(
        ax: Axes, n: int,
        extent: Iterable = [0.2, 0.2, 0.6, 1.0],
        **kwargs) -> Axes:
    """Uses the location of an existing axes to create another axes in relative
    coordinates. IMPORTANT: Unlike ``inset_axes``, this function propagates 
    ``*args`` and ``**kwargs`` to the ``pyplot.axes()`` function, which allows
    for the use of the projection ``keyword``.

    Parameters
    ----------
    ax : Axes
        Existing axes
    n : int
        label, necessary, because matplotlib will replace nonunique axes
    extent : list, optional
        new position in axes relative coordinates,
        by default [0.2, 0.2, 0.6, 1.0]


    Returns
    -------
    Axes
        New axes


    Notes
    -----

    DO NOT CHANGE THE INITIAL POSITION, this position works DO NOT CHANGE!

    :Author:
        Lucas Sawade (lsawade@princeton.edu)

    :Last Modified:
        2021.07.13 18.30

    """

    # Create new axes DO NOT CHANGE THIS INITIAL POSITION
    newax = plt.axes([0.0, 0.0, 0.25, 0.1], label=str(n), **kwargs)

    # Get new position
    ip = InsetPosition(ax, extent)

    # Set new position
    newax.set_axes_locator(ip)

    # return new axes
    return newax



if __name__ == "__main__":

    # 
    outdir = sys.argv[1]

    plot_all_costs(outdir)
    plot_all_models(outdir)
    plot_hessians(os.path.join(outdir, 'inversion00'))
    