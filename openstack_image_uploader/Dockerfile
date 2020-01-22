FROM ubuntu:latest
LABEL maintainer="John Gruber <j.gruber@f5.com>"

WORKDIR /

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --no-install-recommends -y python-glanceclient \
    git

## INJECT_PATCH_INSTRUCTION ##
RUN git clone https://github.com/f5devcentral/tmos-cloudinit.git

VOLUME ["/TMOSImages"]

ENV TMOS_IMAGE_DIR '/TMOSImages'

ENTRYPOINT [ "/tmos-cloudinit/openstack_image_uploader/openstack_glance_image_uploader.py" ]

