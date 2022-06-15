# Run in HPC clusters

In supported clusters (currently Slurm and LSF), ```nnmk``` will also create a ```job.bash``` file. You can directly submit job.bash to the scheduler.

Cluster jobs also require a ```walltime``` property. If a job lasts longer than its requested walltime, nnodes will save and resubmit. You can disable auto resubmission by adding a property ```resubmit = False```.


## Cluster support
Nnodes has no strong connection with any specific job system, when running MPI tasks it just serves as a wrapper for commands like ```mpiexec```, ```srun```, ```jsrun```, etc. So it is easy to add a new cluster configuration with the configuration file. Nnodes has built-in support for:
- Slurm
- LSF
- Local computer with multiprocessing
