#!/bin/sh
# Ensure packaged EN prompts are visible to Asterisk and recordings dir exists.
set -eu
mkdir -p /lab/recordings /var/lib/asterisk/sounds
if [ -d /usr/share/asterisk/sounds/en ] && [ ! -e /var/lib/asterisk/sounds/en ]; then
  ln -sfn /usr/share/asterisk/sounds/en /var/lib/asterisk/sounds/en
fi
