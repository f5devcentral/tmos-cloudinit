FROM ubuntu:latest
LABEL maintainer="John Gruber <j.gruber@f5.com>"

WORKDIR /

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --no-install-recommends -y python-pip \
    python-setuptools \
    git

## INJECT_PATCH_INSTRUCTION ##
RUN git clone https://github.com/f5devcentral/tmos-cloudinit.git
RUN pip install wheel bdist-wheel-name ibm-cos-sdk

VOLUME ["/TMOSImages"]

ENV TMOS_IMAGE_DIR '/TMOSImages'

ENTRYPOINT [ "/tmos-cloudinit/ibmcloud_image_uploader/ibmcloud_cos_image_uploader.py" ]

