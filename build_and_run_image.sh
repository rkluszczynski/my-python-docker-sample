#!/usr/bin/env bash

SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

DOCKER_IMAGE_NAME=python-docker-sample
DOCKER_IMAGE_TAG=latest

DOCKER_INSTANCE_NAME=python-docker-sample

docker stop ${DOCKER_INSTANCE_NAME}
docker rm --force ${DOCKER_INSTANCE_NAME}

docker build -t ${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG} ./
docker push ${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}

#docker run -p 9000:9000 -v "${SCRIPTS_DIR}"/../.env:/app/.env:ro --name ofertomat-4h ${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}
docker run -p 9011:9000 --name ${DOCKER_INSTANCE_NAME} ${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}
