FROM ubuntu:18.04
LABEL maintainer="John Gruber <j.gruber@f5.com>"

WORKDIR /

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    python-jsonschema \
    python-yaml \
    python-pip \
    python-setuptools \
    python-wheel \
    git

## INJECT_PATCH_INSTRUCTION ##
RUN git clone https://github.com/f5devcentral/tmos-cloudinit.git
RUN pip install pycdlib jinja2

ENV LIBGUESTFS_BACKEND=direct

VOLUME ["/declarations", "/configdrives"]

ENV USER 'root'

ENTRYPOINT [ "/tmos-cloudinit/tmos_cidata_builder/tmos_cidata_builder.py" ]

