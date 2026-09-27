#!/bin/sh
# Launch PomoTux inside the sandbox. Resolves the BaseApp's versioned
# site-packages at runtime so SDK updates don't break imports.
PYDIR=$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib", vars={"base": "/app", "platbase": "/app"}))')
export PYTHONPATH="$PYDIR:${PYTHONPATH}"
exec python3 /app/share/pomotux/main.py "$@"
