#!/usr/bin/env python
from os import curdir
from os.path import abspath
from sys import argv, path
from importlib import import_module

from nnodes import root


def bin():

    # Get Current dir
    cwd = abspath(curdir)
    
    # Append current working directory to system path for the import of the 
    # module that contains the workflow. In most cases, the workflow is part
    # of a package s.t. importing is not an issue. But in the case that it is
    # not we better append the path.
    if cwd not in path:
        path.append(cwd)

    # read or create config.toml
    try:
        root.init()
    
    except:
        create_config()
        root.init()
    
    # Write submission script to job.bash
    root.rm('job.bash')

    if len(argv) > 1:
        root.job.create(argv[1])

    else:
        root.job.create()


def create_config():
    from nnodes import job

    config = {'job': {}, 'root': {}}

    print('Welcome to nnodes!')
    print('Select the environment you are using:')

    clusters = []
    cluster_keys = {}

    for key in job.__dir__(): # type: ignore
        if key == 'Job' or key.startswith('_'):
            continue
        
        cls = getattr(job, key)

        if hasattr(cls, 'nnmk_name'):
            clusters.append(cls)
            cluster_keys[cls] = key

    for i, cls in enumerate(clusters):
        print(f'{i}: {cls.nnmk_name}')
    
    print(f'{len(clusters)}: Custom')
    clusters.append('_')
    cluster = input_arr(clusters)
    
    if cluster == '_':
        jmod, modname = input_str('Enter the Python module containing the Job class: ', lambda name: import_module(name), 'invalid module path')
        cluster, clsname = input_str('Enter the name of the Job class: ', lambda name: getattr(jmod, name), 'invalid class name')
        config['job']['system'] = [modname, clsname]

    else:
        config['job']['system'] = ['nnodes.job', cluster_keys[cluster]]
    
    if not hasattr(cluster, 'cpus_per_node'):
        config['job']['cpus_per_node'] = int(input_float('Enter the number of CPUs per node: '))
    
    if not hasattr(cluster, 'cpus_per_node'):
        config['job']['gpus_per_node'] = int(input_float('Enter the number of GPUs per node (0 if not using GPU): '))
    
    if cluster.no_scheduler:
        config['job']['nnodes'] = int(input_float('Enter the number of CPUs available: '))
        config['job']['walltime'] = 1000000

    else:
        config['job']['nnodes'] = int(input_float('Enter the number of nodes to request: '))
        config['job']['walltime'] = input_float('Enter the walltime to request (in minutes): ')
    
    tmod, modname = input_str('Enter the module or file containing the main task: ', lambda name: import_module(name), 'invalid module path')
    _, clsname = input_str('Enter the function name of the main task: ', lambda name: getattr(tmod, name), 'invalid function name')
    config['root']['task'] = [modname, clsname]

    root.dump(config, 'config.toml')
    print('config.toml is created, run with nnrun or submit job script.')


def input_arr(arr):
    try:
        return arr[int(input())]
    
    except KeyboardInterrupt:
        exit()
    
    except:
        print(f'Please enter number from 0 to {len(arr)-1}.')
        return input_arr(arr)


def input_str(prompt, check, err):
    try:
        val_str = input(prompt)
        val = check(val_str)

        return val, val_str
    
    except KeyboardInterrupt:
        exit()
    
    except:
        print(err)
        return input_str(prompt, check, err)

def input_float(prompt):
    try:
        return float(input(prompt))
    
    except KeyboardInterrupt:
        exit()
    
    except:
        print(f'Please enter a valid number.')
        return input_arr(prompt)
