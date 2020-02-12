#!/bin/bash

env > env_file

script_dir=$(dirname $(readlink -f $0))
have_image=$(docker images|grep tmos_demo_setup|grep latest|wc -l)
if [ "$have_image" != "1" ]
then
   cwd=$(pwd)
   cd $script_dir
   echo "building demo setup container ... "
   docker build --rm -t tmos_demo_setup:latest .
   cd ${cwd}
fi

docker run --rm -i -t --env-file=env_file -v $script_dir:/tmos-cloudinit/demo -u $(id -u ${USER}):$(id -g ${USER}) tmos_demo_setup:latest

rm env_file