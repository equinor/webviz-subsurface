#!/bin/bash

set -e

echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin

docker push webviz/example_subsurface_image:equinor-theme

