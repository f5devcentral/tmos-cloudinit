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
    pip install -r /tmos-cloudinit/ibmcloud_vpc_image_importer/requirements.txt

ENV API_KEY ''

ENTRYPOINT [ "/tmos-cloudinit/ibmcloud_vpc_image_importer/ibmcloud_vpc_image_importer.py" ]

