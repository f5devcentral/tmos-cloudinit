FROM ubuntu:18.04
LABEL maintainer="John Gruber <j.gruber@f5.com>"

WORKDIR /

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    python-requests \
    python-pip \
    python-setuptools \
    build-essential \
    python-dev

## INJECT_PATCH_INSTRUCTION ##
RUN pip install wheel python-keystoneclient python-glanceclient python-novaclient python-neutronclient pystache

ENV USER 'root'

ENTRYPOINT [ "/tmos-cloudinit/demo/populate_demo_environment.py" ]
