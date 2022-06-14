# Run in HPC clusters

In supported clusters (currently Slurm and LSF), ```nnmk``` will also create a ```job.bash``` file. You can directly submit job.bash to the scheduler.

Cluster jobs also require a ```walltime``` property. If a job lasts longer than its requested walltime, nnodes will save and resubmit. You can disable auto resubmission by adding a property ```resubmit = False```.
