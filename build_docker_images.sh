#!/bin/bash
now=$(date +%s)

sed -i "/## INJECT_PATCH_INSTRUCTION ##/c\RUN echo ${now}" tmos_image_patcher/Dockerfile
docker build --rm -t tmos_image_patcher:latest tmos_image_patcher
git checkout tmos_image_patcher/Dockerfile

sed -i "/## INJECT_PATCH_INSTRUCTION ##/c\RUN echo ${now}" tmos_configdrive_builder/Dockerfile
docker build --rm -t tmos_configdrive_builder:latest tmos_configdrive_builder
git checkout tmos_configdrive_builder/Dockerfile

sed -i "/## INJECT_PATCH_INSTRUCTION ##/c\RUN echo ${now}" ibmcloud_image_uploader/Dockerfile
docker build --rm -t ibmcloud_image_uploader:latest ibmcloud_image_uploader
git checkout ibmcloud_image_uploader/Dockerfile

sed -i "/## INJECT_PATCH_INSTRUCTION ##/c\RUN echo ${now}" openstack_image_uploader/Dockerfile
docker build --rm -t openstack_image_uploader:latest openstack_image_uploader
git checkout openstack_image_uploader/Dockerfile
