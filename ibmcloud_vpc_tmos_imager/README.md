# TMOS Image IBM Public Cloud VPC Imager

This containerized solution performs the necessary workflow integrating `tmos_image_patcher`,`ibmcloud_image_uploader`, and `ibmcloud_vpc_image_importer` into a single invocation. The intent is to reduce the complexity of creating IBM VPC Gen2 custom TMOS images. This is accomplished by removing much of the flexibility of the individual elements and enforcing a simplified use pattern.

All IBM COS resources are considered ephemeral for this process. They are created and destroyed. The image catalog will not be available when the container run is complete.

The container functionality is driven by environment variables. The following environment variables are supported:

| ENV Variable | Default | Required | Description |
| :---------- | :------- | :-------- | :----------- |
| API_KEY | None | Yes | IAM API key with access to the VPC Gen2 IaaS |
| REGION | us-south | Yes | Which regions in the catalog to import |

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
