import os
import shutil 

import _pickle as pickle


def write_pickle(filename, obj):
    with open(filename, 'wb') as f:
        pickle.dump(obj, f)


def read_pickle(filename):
    with open(filename, 'rb') as f:
        obj = pickle.load(f)

    return obj

def checkdir(cdir):
    """Checks whether a directory exists and if not creates the full path."""
    if not os.path.exists(cdir):
        os.makedirs(cdir)


def removedir(cdir):
    """Removes a directory recursively"""
    shutil.rmtree(cdir)



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

    # return modldir, metadir, datadir, syntdir, frecdir, costdir, graddir, \
    #     hessdir, descdir, optdir
