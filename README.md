# nnodes

Nnodes is a simple workflow manager for Python functions and command line tools. It makes your life easier when running complicated jobs either in your local computer or in a large-scale cluster.

[Documentation](https://icui.github.io/nnodes/index.html)

Intro slides ([PDF](https://raw.githubusercontent.com/icui/nnodes/main/doc/slides.pdf)), poster ([PDF](https://raw.githubusercontent.com/icui/nnodes/main/doc/poster.pdf))

## Features

- **Progress control**.
- **MPI execution**.
- **Parameter management**.
- **Directory utility**.

## Why nnodes?
Workflow manager is essential for many scientific applications and there is a large number of existing workflow managers available. Many of them are mature and well maintained (see [Workflows Community](https://workflows.community) for a comprehensive list). However, we believe that nnodes still has unique advantages. In short, it is simpler than most general-purpose workflow managers and more flexible than most problem-specific workflow managers.

- **Simplicity**. Most professional workflow managers have very steep learning curves, and are sometimes deeply bound with specific computing architectures. Nodes, on the other hand, provides a unified interface for all operations and utilizes only high level APIs. Migrating existing workflows to nnodes is seamless in most cases.
- **Flexibility**. Nnodes is not tied to a specific scientific problem, and it is decided by the user how deeply they wish to integrate their projects with nnodes. Users can simply use nnodes as a progress controller, or MPI executor, which requires little code change, or they can go so far as to let nnodes manage their entire project.
- **Portability**. Nnodes currently supports Slurm and LSF systems but also has API for users to define their custom environment. The workflow is saved in a single pickle file that can be transferred to a new system and continue from where it was left off. The MPI executor adapts automatically so no manual configuration is needed to utilize the full cluster resources.


## Alternatives
If you are looking for more options, below are some projects worth checking out:

- [Ensemble Toolkit](https://radical-cybertools.github.io/entk/index.html)
- [FireWorks](https://materialsproject.github.io/fireworks/)
- [Workflows Community](https://workflows.community)
