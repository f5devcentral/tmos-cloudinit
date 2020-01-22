#!/bin/bash
source /data/F5Download/admin-openrc.sh
iControlLXPackagesDir=/data/iControlLXLatestBuild
imagesDir=/data/F5Download/BIGIP-TEST
version=14.1.2-0.0.37
external_network_name=public
management_network_name=management
cluster_network_name=HA
internal_network_name=internal
vip_network_name=external
ltm_1slot_image_name="BIGIP-${version}.LTM_1SLOT"
ltm_1slot_flavor=LTM.1SLOT
all_1slot_image_name="BIGIP-${version}.ALL_1SLOT"
all_1slot_flavor=ALL.1SLOT
webhook_uuid=$(./generate_webhook_uuid.py)
phone_home_url_view="https://webhook.site/#!/${webhook_uuid}"
phone_home_url="https://webhook.site/${webhook_uuid}"
openstack flavor list | grep LTM.1SLOT | cut -d' ' -f2

docker run --rm -it -v "${imagesDir}":/TMOSImages -v "${iControlLXPackagesDir}":/iControlLXPackages tmos_image_patcher:latest

openstack image delete $all_1slot_image_name
openstack image delete $ltm_1slot_image_name

docker run --rm -it -v "${imagesDir}":/TMOSImages -e OS_USERNAME=$OS_USERNAME -e OS_PASSWORD=$OS_PASSWORD -e OS_AUTH_URL=$OS_AUTH_URL openstack_image_uploader:latest 

allimage=$(openstack image list | grep ${all_1slot_image_name} | cut -d' ' -f2)
echo "ALL image is: ${allimage}"
ltmimage=$(openstack image list | grep ${ltm_1slot_image_name} | cut -d' ' -f2)
echo "LTM image is: ${ltmimage}"
rtdir=$(pwd)
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${scriptdir}/demo/openstack/heat/
sed -i "/ tmos_image/c\  tmos_image: ${ltmimage}" *do_only_env.yaml
sed -i "/ tmos_image/c\  tmos_image: ${allimage}" *waf_env.yaml

os_networks=$(openstack network list)
external_network=$(echo "${os_networks}" | grep ${external_network_name} | cut -d' ' -f2)
management_network=$(echo "${os_networks}" | grep ${management_network_name} | cut -d' ' -f2)
cluster_network=$(echo "${os_networks}" | grep ${cluster_network_name} | cut -d' ' -f2)
internal_network=$(echo "${os_networks}" | grep ${internal_network_name} | cut -d' ' -f2)
vip_network=$(echo "${os_networks}" | grep ${vip_network_name} | cut -d' ' -f2)
vip_subnet_line=$(echo "${os_networks}" | grep ${vip_network_name})
vip_subnet=$(echo ${vip_subnet_line} | cut -d' ' -f6)


sed -i "/ external_network/c\  external_network: ${external_network}" *_env.yaml
sed -i "/ management_network/c\  management_network: ${management_network}" *_env.yaml
sed -i "/ cluster_network/c\  cluster_network: ${cluster_network}" *_env.yaml
sed -i "/ internal_network/c\  internal_network: ${internal_network}" *_env.yaml
sed -i "/ vip_network/c\  vip_network: ${vip_network}" *_env.yaml
sed -i "/ vip_subnet/c\  vip_subnet: ${vip_subnet}" *_env.yaml

ltm_1slot_flavor_id=$(openstack flavor list | grep ${ltm_1slot_flavor} | cut -d' ' -f2)
all_1slot_flavor_id=$(openstack flavor list | grep ${all_1slot_flavor} | cut -d' ' -f2)

sed -i "/ tmos_flavor/c\  tmos_flavor: ${ltm_1slot_flavor_id}" *do_only_env.yaml
sed -i "/ tmos_flavor/c\  tmos_flavor: ${all_1slot_flavor_id}" *waf_env.yaml

sed -i "/ monitor at/c\  # monitor at: ${phone_home_url_view}" *_env.yaml
sed -i "/ phone_home_url/c\  phone_home_url: ${phone_home_url}" *_env.yaml

cd ${rtdir}

echo "follow webhook progress at: ${phone_home_url_view}"