FROM ubuntu:18.04
LABEL maintainer="John Gruber <j.gruber@f5.com>"

WORKDIR /

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    python-requests \
    python-pip \
    python-setuptools \
    git

## INJECT_PATCH_INSTRUCTION ##

RUN git clone https://github.com/f5devcentral/tmos-cloudinit.git

ENV USER 'root'

ENTRYPOINT [ "/tmos-cloudinit/demo/bigiq_regkey_pool_cleaner_connect/bigiq_regkey_pool_cleaner_connect.py", "-d" ]
