#!/bin/sh
# One-time setup for passwordless site blocking. Run once with sudo:
#   sudo ./packaging/block-helper/install.sh
# (deb/rpm packages do this automatically at install.)
set -eu
cd "$(dirname "$0")/../.."
install -Dm755 packaging/block-helper/pomotux-hosts /usr/bin/pomotux-hosts
install -Dm644 packaging/block-helper/io.github.pomotux.rules \
  /usr/share/polkit-1/rules.d/io.github.pomotux.rules
echo "Done. Restart PomoTux: blocking will no longer ask for a password."
