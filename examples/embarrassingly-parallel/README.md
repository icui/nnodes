# Run Embarrassingly Parallel example 

This example can work technically on a local machine, but is aimed at running
a loop on a cluster embarrassingly parallel. If you want to run it locally, 
See changes you have to make at the very bottom of this document.

## Getting nnodes

First activate `nnodes` environment

```
conda activate nnodes-env
```

If you don't have `nnodes` yet:

1. Create an environment 
```
conda create -n nnodes-env "python>=3.10"
```
2. Activate `nnodes` environment
```
conda activate nnodes-env
```
3. Download `nnodes` 
```
git clone git@github.com:icui/nnodes.git
```
4. Enter `nnodes` directory 
```
cd nnodes
```
5. Install `nnodes`
```
pip install -e .
```

## Running the example

Change your directory to `./nnodes/examples/embarrassingly-parallel`.

Since we want to run this example on a cluster, we need to submit a job. An
example script for Princeton's Tiger cluster is shown `slurm.sh`. `slurm.sh`
uses the call `nnrun` to first check the `config.toml` file for the job
configuration and then it runs `hello.py` using `config.toml`.

So, to submit the example on Tiger simply:

```sbatch slurm.sh```

For more details on the `config.toml` and functions in `hello.py`, please see
the [Documentation](https://icui.github.io/nnodes/index.html). 


## Running Locally 

IMPORTANT: The current `config.toml` is set to work with Princeton's Tiger
Cluster, which means the `.add_mpi()` call will use `srun` to submit jobs like
shown above. `srun` is usually not available on a local machine and the hardware
configuration, i.e., number of cores on a local machine will likely not match
either. If you want to run the example locally, change

``` 
[job] 
system = ["nnodes.job", "Tiger"] 
... 
```

to

```
[job] 
system = ["nnodes.job", "Local"] 
...
```
