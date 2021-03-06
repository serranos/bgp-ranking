#!/bin/bash

# This script write ${CONFIG_PATH} in every files where ${VARIABLE} is found.
# Like this it is possible to modify on a simple way the path to the config file for every files using it. 
# The other advantage of this method is that all the python files knows the absolute path to the config file,
# each of them is usable from everywhere.


ROOT_PROJECT="/mnt/data/gits/bgp-ranking/"
VARIABLE="config_file ="
#CONFIG_PATH="\/mnt\/data\/gits\/bgp-ranking\/etc\/bgp-ranking.conf"
CONFIG_PATH="\/path\/to\/bgp-ranking.conf"


find ${ROOT_PROJECT} -name "*.py" -exec sed -i 's/\('"${VARIABLE}"'\).*$/\1 "'"${CONFIG_PATH}"'"/' {} \;


# This path should be the root directory of the project

VARIABLE="root ="
#CONFIG_PATH="\/mnt\/data\/gits\/bgp-ranking"
CONFIG_PATH="\/path\/to\/project\/root\/dir"

find ${ROOT_PROJECT} -name "bgp-ranking.conf" -exec sed -i 's/\('"${VARIABLE}"'\).*$/\1 '"${CONFIG_PATH}"'/' {} \;


# This path should contain the clone of the repository of redis

VARIABLE="PREFIX="
#CONFIG_PATH="\/home\/raphael"
CONFIG_PATH="\/path\/to\/project\/prefix"
find ${ROOT_PROJECT} -name "common.source.sh" -exec sed -i 's/\('"${VARIABLE}"'\).*$/\1"'"${CONFIG_PATH}"'"/' {} \;

