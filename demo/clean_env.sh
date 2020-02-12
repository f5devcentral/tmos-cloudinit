#!/bin/bash
find . -type f -name config.yaml -exec rm {} +
find . -type f -name env.yaml -exec rm {} +
find . -type f -name '*.retry' -exec rm {} +
find . -type f -name variables.tf -exec rm {} +
find . -type f -name 'terraform.tfstate*' -exec rm {} +
find . -type f -name local_defaults.json -exec rm {} +
find . -type d -name '.terraform' -exec rm -rf {} +
