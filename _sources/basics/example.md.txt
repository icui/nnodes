# Run examples

## Run example workflow (Gaussian inversion, requires numpy)
```sh
git clone https://github.com/icui/nnodes
cd nnodes/examples/gaussian
nnrun
```

## Create a new workspace and run test workflow
```
mkdir test
cd test
curl https://raw.githubusercontent.com/icui/nnodes/main/examples/test/workflow.py > workflow.py
nnmk && nnrun
```
Enter ```workflow``` when prompt ```module containing the main task```.<br>
Enter ```main``` when prompt ```function name of the main task```.