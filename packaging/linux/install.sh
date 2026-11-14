#!/bin/sh
# Install pasc for the current user (no root needed):
#	~/.local/lib/pasc     the program
#	~/.local/bin/pasc     a link to it
# Run it from the unpacked pasc-VERSION-linux-x86_64 directory:  ./install.sh
# To install for everyone instead:  sudo ./install.sh /usr/local
set -e
prefix=${1:-$HOME/.local}
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$prefix/lib" "$prefix/bin"
rm -rf "$prefix/lib/pasc"
cp -R "$here/pasc" "$prefix/lib/pasc"
cp "$here/README.md" "$prefix/lib/pasc/" 2>/dev/null || true
ln -sf "$prefix/lib/pasc/pasc" "$prefix/bin/pasc"
echo "pasc installed in $prefix/bin/pasc"
case ":$PATH:" in
*":$prefix/bin:"*)
	;;
*)
	echo "Add $prefix/bin to your PATH, for example by adding this line to ~/.profile:"
	echo "	export PATH=\"$prefix/bin:\$PATH\""
	;;
esac
