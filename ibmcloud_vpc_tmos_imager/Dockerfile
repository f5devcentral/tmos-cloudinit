FROM ubuntu:18.04
LABEL maintainer="John Gruber <j.gruber@f5.com>"

WORKDIR /

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --no-install-recommends -y libguestfs-tools \
    qemu-utils \
    linux-image-generic \
    virtualbox \
    python-guestfs \
    python-crypto \
    python-jsonschema \
    python-yaml \
    git

## INJECT_PATCH_INSTRUCTION ##
RUN git clone https://github.com/f5devcentral/tmos-cloudinit.git && \
    pip install -r /tmos-cloudinit/ibmcloud_vpc_tmos_imager/requirements.txt

ENV LIBGUESTFS_BACKEND=direct

VOLUME ["/TMOSImages", "/iControlLXPackages", "/TMOS_usr", "/TMOS_config"]

ENV TMOS_IMAGE_DIR '/TMOSImages'
ENV TMOS_ICONTROLLX_DIR '/iControlLXPackages'
ENV TMOS_CLOUDINIT_CONFIG_TEMPLATE '/tmos-cloudinit/image_patch_files/cloudinit_configs/default/cloud-init.tmpl'
# ENV TMOS_USR_INJECT_DIR '/tmos-cloudinit/image_patch_files/usr'
ENV USER 'root'
ENV UPDATE_CLOUDINIT 'true'
ENV IMAGE_OVERWRITE = 'no'

ENTRYPOINT [ "/tmos-cloudinit/ibmcloud_vpc_tmos_imager/ibmcloud_vpc_tmos_imager.py" ]

