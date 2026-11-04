#!/usr/bin/env bash
# Una revision, sin iniciar Jobs ni modificar Azure. No depende del directorio actual.
set -euo pipefail
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/revisar_operacion.py" "$@"
