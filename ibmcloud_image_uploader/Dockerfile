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
RUN pip install ibm-cos-sdk

VOLUME ["/TMOSImages"]

ENV TMOS_IMAGE_DIR '/TMOSImages'

ENTRYPOINT [ "/tmos-cloudinit/ibm_cos_patcher/ibm_cos_image_patcher.py" ]

