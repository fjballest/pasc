#!/bin/sh
# Regenerate the PDFs of the documents in docs/ (and, with -s, the pascdb
# screenshots they include first).  usage: docs/build.sh [-s]
set -e
d=$(cd "$(dirname "$0")" && pwd)
[ "$1" = -s ] && python3 "$d/shots.py"
for f in design userguide; do
	"$d/../packaging/docs/md2pdf" "$d/$f.md" "$d/$f.pdf"
done
