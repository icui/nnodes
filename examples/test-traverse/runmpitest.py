from mpi4py import MPI
import time
import datetime
from random import randint
comm = MPI.COMM_WORLD
rank = comm.Get_rank()

import datetime

print(f"{rank:>05d}[START]", str(datetime.datetime.now()))
time.sleep(2)
print(f"{rank:>05d} [STOP]", str(datetime.datetime.now()))
