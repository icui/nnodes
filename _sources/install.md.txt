# Install

There are two ways to install nnodes: PYPI and GitHub. The default version of nnodes require Python 3.10 or later, but a GitHub branch for older Python versions is also available.

## PYPI (Python >= 3.10)
```
pip install nnodes
```

## GitHub
Installing from GitHub offers more flexibility. You can optionally install in editable mode (add ```-e``` after ```pip install```) so that the changes you make to the Git directory will directly reflect to the nnodes Python module.

```main``` branch is recommended for most users and is the default branch.
```
git clone https://github.com/icui/nnodes
cd nnodes
pip install .
```

```devel``` branch is offers that latest improvements but is not stable. Use for testing only.
```
git clone https://github.com/icui/nnodes --branch=devel
```

```3.7``` branch is a temporary solution for users using Python 3.7 - 3.9, but is not fully tested.
```
git clone https://github.com/icui/nnodes --branch=3.7
```