#!/usr/bin/env bash
# Solo lectura o what-if. No hay modo aplicar ni llamadas job start.
set -euo pipefail
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/consolidar_azure.py" "$@"
