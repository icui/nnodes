#!/bin/bash
#SBATCH --job-name=nnodes-embarrassingly-parallel     # create a short name for your job
#SBATCH --output=nnodes-embarrassingly-parallel.out # stdout file
#SBATCH --error=nnodes-embarrassingly-parallel.err  # stderr file
#SBATCH --nodes=1                 # node count
#SBATCH --ntasks=30               # total number of tasks across all nodes
#SBATCH --mem=100G                # memory per cpu-core (4G is default)
#SBATCH --time=00:02:00           # total run time limit (HH:MM:SS)


echo "My SLURM_ARRAY_JOB_ID is $SLURM_ARRAY_JOB_ID."
echo "Executing on the machine:" $(hostname)

module purge
module load anaconda3/2020.11
conda activate nnodes-env

# Change directory to the Job directory containing the `config.toml`
# cd workflowdir
nnrun