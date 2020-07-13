# TMOS Image IBM Public Cloud VPC Imager

This containerized solution performs the necessary workflow integrating `tmos_image_patcher`,`ibmcloud_image_uploader`, and `ibmcloud_vpc_image_importer` into a single invocation. The intent is to reduce the complexity of creating IBM VPC Gen2 custom TMOS images. This is accomplished by removing much of the flexibility of the individual elements and enforcing a simplified use pattern.

This container assumes association between BIG-IP qcow2.zip files from downloads.f5.com and IBM VPC custom image name based on the BIG-IP image naming convention.

```BIGIP.x.y.z-n.n.nnn.type-1SLOT.qcow2.zip``` -> ```bigip-x-y-z-n-n-nnn-type-1slot-region```

By default, the discovered BIG-IP images found in the TMOSImages volume will be synchronized to the region(s) specified in the REGION environment variable. If a IBM VPC custom starting with ```bigip``` is found in a region without a corresponding disk image in TMOSImages, the IBM VPC image will be delete. This can be alterred by changing the default behavior using the ```DELETE_VPC_IMAGE``` environment variable.

There is also a convience ```DELETE_ALL``` environment variable which will simply delete all VPC custom images starting ```bigip``` and exit.

All IBM COS resources are considered ephemeral for this process. They are created and destroyed. The image catalog will not be available when the container run is complete. The IBM COS resources are named randomly to assue uniquness.

The container functionality is driven by environment variables. The following environment variables are supported:

| ENV Variable | Default | Required | Description |
| :---------- | :------- | :-------- | :----------- |
| API_KEY | None | Yes | IAM API key with access to the VPC Gen2 IaaS |
| REGION | us-south | Yes | Which regions in the catalog to import, either a single or comma separated list |
| DELETE_ALL | false | No | Delete all custom images in the specified region only |
| DELETE_VPC_IMAGE | true | No | Delete any VPC images which are not present in the TMOSImages directory |
| UPDATE_IMAGES | false | No | Force update all custom images matching images in the TMOSImages directory |

The same container volume mounts used for `tmos_image_patcher` are required.

| Docker Volume Mount | Required | Description |
| --------------------- | ----- | ---------- |
| /TMOSImages   | Yes | Path to the directory with the TMOS Virtual Edition archives to patch |
| /iControlLXPackages   | No | Path to the directory with optional iControl LX RPM packages to inject into the images |

## Using the Docker Container

Build the docker container

`
docker build -t ibmcloud_vpc_tmos_imager:latest .
`

Set environment variables in your shell (bash used in example)

```bash
export API_KEY='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
export REGION='us-south,us-east,eu-gb,eu-de'
```

Run the container with the supplying environment variables.

```bash
docker run --rm -it -v /data/BIGIP-HF01:/TMOSImages -v /data/iControlLXLatestBuild:/iControlLXPackages  -e API_KEY="$API_KEY" -e REGION="$REGION"  ibmcloud_vpc_tmos_imager:latest
```
