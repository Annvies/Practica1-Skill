#!/usr/bin/env bash
# ============================================================================
#  Demostracion de code-study-flashcards (Linux / macOS / Git Bash)
#
#  Uso:   bash scripts/demo.sh
#
#  Ejecuta un caso exitoso y cinco casos de error, comprobando el codigo de
#  salida de cada paso. Equivalente a scripts/demo.bat.
# ============================================================================
set -u

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SALIDA="$RAIZ/output"
EJEMPLOS="$RAIZ/examples"
SCRIPT="$RAIZ/scripts/generate_cards.py"
mkdir -p "$SALIDA"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

TOTAL=0
FALLOS=0

titulo() {
  echo
  echo "=========================================================================="
  echo "  $1"
  echo "=========================================================================="
}

verificar() {
  local esperado="$1" actual="$2"
  TOTAL=$((TOTAL + 1))
  if [ "$actual" = "$esperado" ]; then
    echo "  [OK] codigo de salida $actual - esperado $esperado"
  else
    FALLOS=$((FALLOS + 1))
    echo "  [FALLO] codigo de salida $actual - se esperaba $esperado"
  fi
}

titulo "0. Version de la skill"
$PY "$SCRIPT" --version
verificar 0 $?

titulo "1. CASO EXITOSO - codigo Python a tarjetas Markdown"
$PY "$SCRIPT" -i "$EJEMPLOS/input_sample.py" -o "$SALIDA/demo_tarjetas.md"
verificar 0 $?

titulo "2. CASO EXITOSO - apuntes Markdown a tarjetas (recorte a 8)"
$PY "$SCRIPT" -i "$EJEMPLOS/notas_sample.md" -o "$SALIDA/demo_notas.md" --max-cards 8
verificar 0 $?

titulo "3. CASO EXITOSO - export a Anki (texto separado por tabuladores)"
$PY "$SCRIPT" -i "$EJEMPLOS/input_sample.py" --format anki -o "$SALIDA/demo_anki.txt" --max-cards 3
verificar 0 $?
echo "Primer registro exportado:"
sed -n '5p' "$SALIDA/demo_anki.txt"
echo

titulo "4. ERROR - el archivo no existe  (se espera 3)"
$PY "$SCRIPT" -i "$EJEMPLOS/no_existe.py"
verificar 3 $?

titulo "5. ERROR - archivo vacio  (se espera 3)"
$PY "$SCRIPT" -i "$EJEMPLOS/empty_sample.py"
verificar 3 $?

titulo "6. ERROR - formato no soportado  (se espera 3)"
$PY "$SCRIPT" -i "$EJEMPLOS/unsupported_sample.pdf"
verificar 3 $?

titulo "7. ERROR - codigo Python con error de sintaxis  (se espera 3)"
$PY "$SCRIPT" -i "$EJEMPLOS/broken_syntax_sample.py"
verificar 3 $?

titulo "8. ERROR - plantilla de assets ausente  (se espera 4)"
$PY "$SCRIPT" -i "$EJEMPLOS/input_sample.py" -o "$SALIDA/demo_tarjetas.md" --template "$RAIZ/assets/no_existe.md"
verificar 4 $?

titulo "9. ERROR - carpeta sin formatos soportados  (se espera 3)"
mkdir -p "$SALIDA/carpeta_vacia"
echo "sin formatos soportados" > "$SALIDA/carpeta_vacia/notas.pdf"
$PY "$SCRIPT" -i "$SALIDA/carpeta_vacia"
verificar 3 $?

titulo "9b. ERROR - uso incorrecto: --max-cards negativo  (se espera 2)"
$PY "$SCRIPT" -i "$EJEMPLOS/input_sample.py" --max-cards -1
verificar 2 $?

titulo "10. Suite de pruebas automatizadas (36 casos)"
$PY -m unittest discover -s "$RAIZ/tests"
verificar 0 $?

titulo "11. Recorrido de una carpeta completa (caso mixto)"
$PY "$SCRIPT" -i "$EJEMPLOS" -r -o "$SALIDA/demo_carpeta.md" --max-cards 20
verificar 0 $?

titulo "Archivos generados"
ls -1 "$SALIDA" | grep '^demo_' || echo "(ninguno)"

echo
echo "=========================================================================="
if [ "$FALLOS" -eq 0 ]; then
  echo "  DEMO COMPLETADA: $TOTAL de $TOTAL pasos con el codigo de salida esperado."
else
  echo "  DEMO CON PROBLEMAS: $FALLOS de $TOTAL pasos con un codigo inesperado."
fi
echo "=========================================================================="
exit "$FALLOS"
