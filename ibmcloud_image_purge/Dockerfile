FROM ubuntu:18.04
LABEL maintainer="John Gruber <j.gruber@f5.com>"

WORKDIR /

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --no-install-recommends -y python-pip \
    python-setuptools \
    python-wheel \
    git

## INJECT_PATCH_INSTRUCTION ##
RUN git clone https://github.com/f5devcentral/tmos-cloudinit.git && \
    pip install -r /tmos-cloudinit/ibmcloud_image_purge/requirements.txt

VOLUME ["/TMOSImages"]

ENV TMOS_IMAGE_DIR '/TMOSImages'
ENV COS_BUCKET_PREFIX 'f5'

ENTRYPOINT [ "/tmos-cloudinit/ibmcloud_image_purge/ibmcloud_image_purge.py" ]

