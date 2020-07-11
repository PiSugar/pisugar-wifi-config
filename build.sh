#!/bin/sh

sudo apt install -y debhelper virtualenv python3-virtualenv python3-all python3-setuptools
virtualenv -p python3 venv
source venv/bin/activate

pip3 install stdeb
python3 setup.py --command-packages=stdeb.command sdist_dsc --with-python2=False \
    --with-python3=True bdist_deb

VER=$(cat setup.py | grep "VERSION.*=" | awk -F '"' '{print $2}')
DEB=$(ls deb_dist | grep "python3-pisugar-wifi-config.*all.deb")

# Fix post install
rm -rf build
fakeroot sh -c "
  set -e
  mkdir -p build/old
  dpkg-deb -R deb_dist/${DEB} build/old
  
  mkdir -p build/old/lib/systemd/system
  mkdir -p build/old/etc/default
  cp -f debian/pisugar-wifi-config.service build/old/lib/systemd/system
  cp -f debian/pisugar-wifi-config.default build/old/etc/default/pisugar-wifi-config

  (cd build/old && md5sum lib/systemd/system/pisugar-wifi-config.service >> DEBIAN/md5sums)
  (cd build/old && md5sum etc/default/pisugar-wifi-config >> DEBIAN/md5sums)

  for s in config templates preinst postinst prerm postrm; do
    cp -f debian/\$s build/old/DEBIAN/
    chmod +x build/old/DEBIAN/\$s
  done
  dpkg-deb -b build/old build/${DEB}
"

echo "DONE!"