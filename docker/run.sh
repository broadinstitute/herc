#!/bin/bash

VENV_DIR=/herc_venv

source $VENV_DIR/bin/activate
herc --debug
deactivate
