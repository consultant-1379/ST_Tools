#!/bin/sh
cat > setup.cfg <<EOF
[build]
executable=/usr/bin/python
[install]
install_lib=/usr/lib64/python2.7/site-packages
install_scripts=/usr/bin
EOF
python setup_sles.py build -e "/usr/bin/python" bdist_rpm --pre-install prein.sh --post-install postin.sh --pre-uninstall preun.sh --post-uninstall postun.sh
rm setup.cfg
