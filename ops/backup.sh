#!/bin/sh
set -eu
umask 077
stamp="$(date -u +%Y-%m-%dT%H%M%SZ)"
pg_dump --format=custom --compress=9 --file="/backups/worldguessr-${stamp}.dump"
find /backups -type f -name 'worldguessr-*.dump' -mtime +6 -delete
