# Dockerfile to build and run tests

FROM alpine:latest
RUN apk add --no-cache \
    swig \
    python3 \
    python3-dev \
    py3-pip \
    py3-setuptools \
    build-base \
    libnfs \
    libnfs-dev \
    sudo
COPY . /app
WORKDIR /app/libnfs
RUN make
WORKDIR /app
RUN sudo python3 setup.py install
CMD ["python3", "-m", "unittest", "discover", "-s", "tests"]