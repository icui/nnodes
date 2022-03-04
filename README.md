# nnodes

A simple workflow manager.

**What nnodes does**

- Provide a tree structure to manage ```tasks``` and properties.
- Save and restore "```task```" progress.
- Manage the parallel execution of multiple MPI calls.
- Offer vairous file system and MPI utilities.

**How nnodes works**

A ```task``` in nnodes can be either a python function or a Shell command. The basic element of nnodes is called ```node```. A ```node``` can contain 0 or 1 ```task``` and any number of child nodes which can be executed either sequentially or concurrently.

**Alternatives**

If you are looking for a more sophisticated workflow manager, below are some options worth checking out:

- [Ensemble Toolkit](https://radical-cybertools.github.io/entk/index.html)
- [FireWorks](https://materialsproject.github.io/fireworks/)
