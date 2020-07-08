# TMOS Image IBM Public Cloud VPC Custom Image Importer

IBM VPC Generation 2 Cloud supports the integration of custom appliance virtual machine images sourced from IBM Public Cloud Cloud Object Storage (COS) SQL URLs. Within a customer VPC, custom images can be imported from their COS SQL URLs.

This python script and packaged Docker container preforms the task of importing TMOS custom images into a VPC provided a API_KEY with privledges the TMOS Image COS SQL URL.

The script functionality is driven by environment variables. This makes it simple to dockerize. The following environment variable are supported:

| ENV Variable | Default | Required | Description |
| :---------- | :------- | :-------- | :----------- |
| TMOS_IMAGE_CATALOG_URL | None | Yes | The HTTP URL to download the F5 catalog of COS SQL URLS (get from F5) |
| API_KEY | None | Yes | IAM API key with access to the VPC Gen2 IaaS |
| IMAGE_MATCH | All images in the catalog will match | No | Regex to limit which images to import (i.e. '^bigip-15') |
| REGION | us-south | Yes | Which regions in the catalog to import |
| DRY_RUN | false | No | Perform a dry run an only report |
| UPDATE_IMAGES | false | No | Delete and update imported images if they exist |
| DELETE_ALL | false | No | Force delete all found imported images matching the IMAGE_MATCH regex |

## Using the Python Script

The python 2 script uses only core elements, as it uses only IBM Cloud REST APIs through the `requests` module.

Set environment variables in your shell (bash used in example)

```bash
export TMOS_IMAGE_CATALOG_URL='https://f5-image-catalog-xxxxxxxxxxxxxx.s3.us-south.cloud-object-storage.appdomain.cloud/f5-image-catalog.json'
export API_KEY='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
export IMAGE_MATCH='^bigip-14'
```

Run the python script

`
./ibmcloud_vpc_image_importer.py
`

## Using the Docker Container

Build the docker container

`
docker build -t ibmcloud_vpc_image_importer:latest .
`

Set environment variables in your shell (bash used in example)

```bash
export TMOS_IMAGE_CATALOG_URL='https://f5-image-catalog-xxxxxxxxxxxxxx.s3.us-south.cloud-object-storage.appdomain.cloud/f5-image-catalog.json'
export API_KEY='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
export IMAGE_MATCH='^bigip-14'
```

Run the container with the supplying environment variables.

```bash
docker run --rm -it -e API_KEY="$API_KEY" -e TMOS_IMAGE_CATALOG_URL="$TMOS_IMAGE_CATALOG_URL" -e IMAGE_MATCH="$IMAGE_MATCH" ibmcloud_vpc_image_importer:latest
```
