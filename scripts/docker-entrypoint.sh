#!/bin/sh
set -eu

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

group_name="$(id -gn appuser)"

if [ "$(id -u appuser)" != "$PUID" ]; then
    usermod -o -u "$PUID" appuser
fi

if [ "$(id -g appuser)" != "$PGID" ]; then
    groupmod -o -g "$PGID" "$group_name"
fi

mkdir -p /app/instance /data /data/phonebooks

# Best effort chown for bind mounts; this may fail on some NAS setups.
chown -R appuser:"$group_name" /app/instance /data 2>/dev/null || true

if [ ! -w /data/phonebooks ]; then
    echo "ERROR: /data/phonebooks is not writable for uid=$(id -u appuser) gid=$(id -g appuser)." >&2
    echo "Set PUID/PGID to your host user or fix host permissions for the bind mount path." >&2
    exit 1
fi

exec su -s /bin/sh appuser -c "$*"
