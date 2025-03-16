#!/bin/bash

mkdir -p ~/.vnc
DISPLAY=:0
export DISPLAY=:0
SCREEN_WIDTH=${SCREEN_WIDTH:-1920}
SCREEN_HEIGHT=${SCREEN_HEIGHT:-1080}
SCREEN_DEPTH=${SCREEN_DEPTH:-16}

echo "Starting Xvfb with screen ${SCREEN_WIDTH}x${SCREEN_HEIGHT}x${SCREEN_DEPTH}"

cd /opt/orbita
Xvfb $DISPLAY -screen 0 ${SCREEN_WIDTH}x${SCREEN_HEIGHT}x${SCREEN_DEPTH} &
sleep 3
x11vnc -storepasswd 12345678 ~/.vnc/passwd
x11vnc -display $DISPLAY -bg -forever -usepw -quiet -rfbport 5901 -xkb

# Check if nginx is already running and stop it
if [ -f /var/run/nginx.pid ]; then
    nginx -s stop
fi

# Start nginx with new configuration
/usr/sbin/nginx -c /etc/nginx/nginx.conf
