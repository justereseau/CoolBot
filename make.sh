#!/usr/bin/env bash

# This script is used to build the project.
sudo apt install python3 python3-venv python3-pip

# Initialise a virtual environment if one does not exist.
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Ensure the requirements are installed.
./venv/bin/pip install -r requirements.txt
