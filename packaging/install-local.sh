#!/bin/sh
# Install the current checkout of pasc (and pascdb) for this machine's user,
# without root: the sources go to ~/.local/lib/pasc and small launchers to
# BINDIR (default /usr/local/bin if writable, else ~/.local/bin).
# Needs python3 3.7 or later.  usage: packaging/install-local.sh [BINDIR]
set -e
src=$(cd "$(dirname "$0")/.." && pwd)
lib="$HOME/.local/lib/pasc"
bindir=${1:-/usr/local/bin}
[ -w "$bindir" ] || bindir="$HOME/.local/bin"
mkdir -p "$lib" "$bindir"
rm -rf "$lib.new"
mkdir "$lib.new"
cp -R "$src/pasc.py" "$src/pasclib" "$src/README.md" "$lib.new/"
[ -e "$src/pascdb.py" ] && cp -R "$src/pascdb.py" "$lib.new/"
[ -e "$src/pasgrade.py" ] && cp -R "$src/pasgrade.py" "$lib.new/"
[ -d "$src/pascdblib" ] && cp -R "$src/pascdblib" "$lib.new/"
find "$lib.new" -name __pycache__ -prune -exec rm -rf {} +
rm -rf "$lib"
mv "$lib.new" "$lib"
for tool in pasc pascdb pasgrade; do
	[ -e "$lib/$tool.py" ] || continue
	rm -f "$bindir/$tool"
	printf '#!/bin/sh\nexec python3 "%s/%s.py" "$@"\n' "$lib" "$tool" > "$bindir/$tool"
	chmod 755 "$bindir/$tool"
	echo "installed $bindir/$tool"
done
