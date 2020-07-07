# TMOS Image IBM Public Cloud COS Uploader

IBM VPC Generation 2 Cloud supports the integration of custom appliance virtual machine images sourced from IBM Public Cloud Cloud Object Storage (COS) SQL URLs. To make patched TMOS Images available to IBM VPC Generation 2 Cloud customers, the TMOS images must first be made available as IBM COS objects.

This python script and packaged Docker container preforms the task of taking local patched TMOS images and creating IBM COS buckets and objects, as well as creating public COS SQL URL catalogs.

The script functionality is driven by environment variables. This makes it simple to dockerize. The following environment variable are supported:

| ENV Variable | Default | Required | Description |
| :---------- | :------- | :-------- | :----------- |
| TMOS_IMAGE_DIR | None | Yes | Directory to look for patched images |
| COS_API_KEY | None | Yes | The COS resource service API key |
| COS_RESOURCE_CRN | None | Yes | The COS resource CRN (id) |
| COS_IMAGE_LOCATION | us-south | Yes | A single or comma-delimited list of regions to upload images |
| COS_AUTH_ENDPOINT | https://iam.cloud.ibm.com/identity/token | No | Set the IBM Cloud auth resource (use for testing) |
| UPDATE_IMAGES | false | No | Delete and update COS object if they exist |
| DELETE_ALL | false | No | Force delete all found COS objects and buckets |

## Using the Python Script ##

Install the python dependencies into your environment (virtualenv suggested)

`pip install -r requirements.txt`

Set environment variables in your shell (bash used in example)

```
export TMOS_IMAGE_DIR='/data/F5Downloads/Latest'
export COS_API_KEY='xxxxxxxxxxxxx_xxxxxxxxxx_xxxxxxxxxxxxxxxxxxx'
export COS_RESOURCE_CRN='crn:v1:bluemix:public:cloud-object-storage:global:a/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx::'
export COS_IMAGE_LOCATION='eu-de,eu-gb,us-east,us-south'
```

Run the python script

`
./ibmcloud_cos_image_uploader.py
`

## Using the Docker Container ##

Build the docker container

`
docker build -t ibmcloud_image_uploader:latest .
`

Set environment variables in your shell (bash used in example)

```
export TMOS_IMAGE_DIR='/data/F5Downloads/Latest'
export COS_API_KEY='xxxxxxxxxxxxx_xxxxxxxxxx_xxxxxxxxxxxxxxxxxxx'
export COS_RESOURCE_CRN='crn:v1:bluemix:public:cloud-object-storage:global:a/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx::'
export COS_IMAGE_LOCATION='eu-de,eu-gb,us-east,us-south'
```

Run the container with the supplying environment variables.

Note: by default the docker container will make the `TMOS_IMAGE_DIR` to the `/TMOSImages` directory inside the container. The example uses an volume to mount the host directory to the `/TMOSImages` directory in the container.

```
docker run --rm -it -v $TMOS_IMAGE_DIR:/TMOSImages -e COS_API_KEY="$COS_API_KEY" -e COS_RESOURCE_CRN="$COS_RESOURCE_CRN" -e COS_IMAGE_LOCATION="$COS_IMAGE_LOCATION" ibmcloud_image_uploader:latest
```
