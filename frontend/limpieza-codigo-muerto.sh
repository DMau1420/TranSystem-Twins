#!/usr/bin/env bash
# Verifica si los archivos candidatos a eliminar siguen importándose.
# Uso (desde frontend/):  bash scripts/limpieza-codigo-muerto.sh
# Con --borrar elimina SOLO los que no tienen ninguna referencia.

set -u
CANDIDATOS=(
  "src/api/mapApi.js"
  "src/components/EdicionPanel.jsx"
  "src/components/SimularBoton.jsx"
  "src/components/BottomProgressBar.jsx"
)
BORRAR=false
[ "${1:-}" = "--borrar" ] && BORRAR=true

for f in "${CANDIDATOS[@]}"; do
  # Si el archivo no está en esa ruta, búscalo por nombre
  if [ ! -f "$f" ]; then
    f=$(find src -name "$(basename "$f")" | head -n 1)
  fi
  if [ -z "$f" ] || [ ! -f "$f" ]; then
    echo "-- no existe: $(basename "${f:-desconocido}")"
    continue
  fi

  nombre=$(basename "$f" | sed -E 's/\.(jsx?|tsx?)$//')
  # Referencias por import/require, excluyendo el propio archivo
  refs=$(grep -rnE "(from|require\()\s*['\"][^'\"]*${nombre}(\.jsx?)?['\"]" src --include=*.js --include=*.jsx --include=*.ts --include=*.tsx | grep -v "^${f}:" || true)

  if [ -z "$refs" ]; then
    echo "SIN USO  $f"
    $BORRAR && rm "$f" && echo "         eliminado"
  else
    echo "EN USO   $f"
    echo "$refs" | sed 's/^/           /'
  fi
done

# Referencias residuales a la ruta /points eliminada en el backend
echo
echo "Referencias a '/points' en src/:"
grep -rn "/points" src || echo "  (ninguna)"