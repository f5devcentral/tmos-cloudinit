#!/bin/bash

# If the DOCKER_REPO varaible is set, assure it ends in forward slash and insert into build

echo "building docker images"
if ! [ -z "$DOCKER_REPO" ]
then
    [[ "${DOCKER_REPO}" != */ ]] && DOCKER_REPO="${DOCKER_REPO}/"
else
    DOCKER_REPO=''
fi

CACHE_OPTION=''
if ! [ -z "$USE_CACHED_IMAGES" ]
then
    CACHE_OPTION='--no-cache'
fi

echo "building TMOS Image Patcher"
docker build --rm ${CACHE_OPTION} -t ${DOCKER_REPO}tmos_image_patcher:latest tmos_image_patcher
echo "building TMOS config drive builder"
docker build --rm ${CACHE_OPTION} -t ${DOCKER_REPO}tmos_configdrive_builder:latest tmos_configdrive_builder
echo "building IBM public cloud object storage uploader"
docker build --rm ${CACHE_OPTION} -t ${DOCKER_REPO}ibmcloud_image_uploader:latest ibmcloud_image_uploader
echo "building OpenStack glance image uploader"
docker build --rm ${CACHE_OPTION} -t ${DOCKER_REPO}openstack_image_uploader:latest openstack_image_uploader
echo "building Demonostration setup container"
docker build --rm ${CACHE_OPTION} -t ${DOCKER_REPO}tmos_demo_setup:latest demo
cwd=$(pwd)
echo "building OpenStack neutron port license revocation container"
cd ${cwd}/demo/openstack/bigiq_regkey_pool_cleaner_neutron_port
docker build --rm ${CACHE_OPTION} -t ${DOCKER_REPO}bigiq_regkeypool_cleaner_neutron_port:latest .
cd ${cwd}/demo/libvirt/bigiq_regkey_pool_cleaner_connect
echo "building connection monitor port license revocation container"
docker build --rm ${CACHE_OPTION} -t ${DOCKER_REPO}bigiq_regkeypool_cleaner_connect:latest .
cd ${cwd}

