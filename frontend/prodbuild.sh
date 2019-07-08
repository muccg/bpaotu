#!/bin/bash

set -e 

cd /frontend

# run production build (under travis)
yarn install
yarn build
