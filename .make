#!/bin/sh
cd ../nnodes/doc
make html
cd -
rm -rf *
mv ../nnodes/doc/build/html/* .