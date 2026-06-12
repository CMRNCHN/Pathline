FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    asterisk \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY docker/asterisk/pjsip.conf      /etc/asterisk/pjsip.conf
COPY docker/asterisk/extensions.conf /etc/asterisk/extensions.conf
COPY docker/asterisk/manager.conf    /etc/asterisk/manager.conf
COPY docker/asterisk/modules.conf    /etc/asterisk/modules.conf
COPY docker/asterisk/http.conf       /etc/asterisk/http.conf
COPY docker/asterisk/ari.conf        /etc/asterisk/ari.conf

EXPOSE 5060/udp 5038/tcp 8088/tcp 10000-10020/udp

CMD ["asterisk", "-f", "-vvv"]
