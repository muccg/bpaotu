#!/bin/bash

set -e

#
# Development build and tests
#

# ccg-composer runs as this UID, and needs to be able to
# create output directories within it
mkdir -p data/ build/
sudo chown 1000:1000 data/ build/
cp .env .env_local

./develop.sh build base
./develop.sh build builder
./develop.sh build dev
./develop.sh run build lint
