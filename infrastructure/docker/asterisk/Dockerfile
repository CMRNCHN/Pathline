FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    asterisk \
    netcat-openbsd \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

COPY docker/asterisk/pjsip.conf                 /etc/asterisk/pjsip.conf
COPY docker/asterisk/pjsip_trunk.conf.template  /etc/asterisk/pjsip_trunk.conf.template
COPY docker/asterisk/extensions.conf            /etc/asterisk/extensions.conf
COPY docker/asterisk/manager.conf               /etc/asterisk/manager.conf
COPY docker/asterisk/modules.conf               /etc/asterisk/modules.conf
COPY docker/asterisk/http.conf                  /etc/asterisk/http.conf
COPY docker/asterisk/ari.conf                   /etc/asterisk/ari.conf
COPY docker/asterisk/entrypoint.sh              /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5060/udp 5038/tcp 8088/tcp 10000-10020/udp

# Entrypoint renders the optional SIP trunk from env vars, then execs Asterisk.
ENTRYPOINT ["/entrypoint.sh"]
