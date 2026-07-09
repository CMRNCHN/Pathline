FROM andrius/asterisk:18-current

USER root

COPY extensions_lab.conf /tmp/extensions_lab.conf
COPY pjsip.lab.conf /tmp/pjsip.lab.conf

# Append lab dialplan and SIP endpoint to the image defaults.
RUN cat /tmp/extensions_lab.conf >> /etc/asterisk/extensions.conf && \
    cat /tmp/pjsip.lab.conf >> /etc/asterisk/pjsip.conf && \
    rm /tmp/extensions_lab.conf /tmp/pjsip.lab.conf

USER asterisk
