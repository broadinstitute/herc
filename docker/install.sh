#!/bin/bash

HERC_DIR=$1
VENV_DIR=$2

cd $HERC_DIR
source $VENV_DIR/bin/activate
python setup.py install
deactivate
