#!/bin/sh
# Installs the public bundled-runtime release; no JDK or Gradle prerequisite.
set -eu
project_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
. "$project_dir/tools/bootstrap_installer.sh"
ensure_installer_python
exec python3 "$project_dir/tools/install_linux.py" "$@"
