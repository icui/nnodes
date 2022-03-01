#!/bin/bash
#SBATCH -t00:40:00
#SBATCH -N 6
#SBATCH -n 156
#SBATCH --output=nnodes.txt
# # SBATCH --reservation=test
#SBATCH --gres=gpu:4

# For parallel computation
# export MKL_NUM_THREADS=1
# export NUMEXPR_NUM_THREADS=1
export OMP_NUM_THREADS=1

module load anaconda3/2020.7 cudatoolkit/10.2 openmpi/gcc

source /usr/licensed/anaconda3/2020.7/etc/profile.d/conda.sh && conda activate lwsspy

cd /home/lsawade/nnodes/source
rm -f root.pickle
python -c "from nnodes import root; root.run()"
