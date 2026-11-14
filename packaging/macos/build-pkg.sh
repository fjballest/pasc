#!/bin/sh
# Build the macOS installer package from the universal2 (Apple silicon and
# Intel) PyInstaller build in dist/pasc.  The package installs it in
# /usr/local/lib/pasc with a /usr/local/bin/pasc link.
# usage: packaging/macos/build-pkg.sh VERSION
set -e
version=$1
root=build/pkgroot
rm -rf build/pkgroot build/scripts
mkdir -p $root/usr/local/lib $root/usr/local/bin build/scripts
cp -R dist/pasc $root/usr/local/lib/pasc
cp README.md $root/usr/local/lib/pasc/
ln -s ../lib/pasc/pasc $root/usr/local/bin/pasc
ln -s ../lib/pasc/pascdb $root/usr/local/bin/pascdb
# files downloaded from the web are quarantined; the installed ones need not be
cat > build/scripts/postinstall <<'EOS'
#!/bin/sh
xattr -dr com.apple.quarantine /usr/local/lib/pasc 2>/dev/null
exit 0
EOS
chmod 755 build/scripts/postinstall
pkgbuild --root $root --identifier org.pasc.pasc --version "$version" \
	--scripts build/scripts --install-location / "dist/pasc-$version-macos.pkg"
