FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION=0.1.8
ARG BUILD_ARCH=amd64

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}"

RUN \
    apk add --no-cache \
        python3 \
        py3-pip \
    && python3 -m venv /opt/airtouch4/venv

WORKDIR /opt/airtouch4

COPY requirements.txt ./
RUN /opt/airtouch4/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY scripts ./scripts
COPY run.sh /run.sh

RUN chmod a+x /run.sh

ENV PYTHONPATH=/opt/airtouch4/src

CMD ["/run.sh"]
