@echo off
setlocal enabledelayedexpansion
REM ===========================================================================
REM  Demostracion de code-study-flashcards (Windows)
REM
REM  Uso:   scripts\demo.bat
REM
REM  Ejecuta un caso exitoso y cinco casos de error, comprobando el codigo de
REM  salida de cada paso. Es el comando de la presentacion: muestra el flujo
REM  completo y tambien el manejo de errores.
REM ===========================================================================

cd /d "%~dp0.."
set "RAIZ=%CD%"
set "SALIDA=%RAIZ%\output"
set "SCRIPT=%RAIZ%\scripts\generate_cards.py"
set "EJEMPLOS=%RAIZ%\examples"
if not exist "%SALIDA%" mkdir "%SALIDA%"

set /a TOTAL=0
set /a FALLOS=0

call :titulo "0. Version de la skill"
python "%SCRIPT%" --version
call :verificar 0

call :titulo "1. CASO EXITOSO - codigo Python a tarjetas Markdown"
python "%SCRIPT%" -i "%EJEMPLOS%\input_sample.py" -o "%SALIDA%\demo_tarjetas.md"
call :verificar 0

call :titulo "2. CASO EXITOSO - apuntes Markdown a tarjetas (recorte a 8)"
python "%SCRIPT%" -i "%EJEMPLOS%\notas_sample.md" -o "%SALIDA%\demo_notas.md" --max-cards 8
call :verificar 0

call :titulo "3. CASO EXITOSO - export a Anki (texto separado por tabuladores)"
python "%SCRIPT%" -i "%EJEMPLOS%\input_sample.py" --format anki -o "%SALIDA%\demo_anki.txt" --max-cards 3
call :verificar 0
echo Primer registro exportado:
powershell -NoProfile -Command "Get-Content -LiteralPath '%SALIDA%\demo_anki.txt' -Encoding utf8 | Select-Object -Skip 4 -First 1"
echo.

call :titulo "4. ERROR - el archivo no existe  (se espera 3)"
python "%SCRIPT%" -i "%EJEMPLOS%\no_existe.py"
call :verificar 3

call :titulo "5. ERROR - archivo vacio  (se espera 3)"
python "%SCRIPT%" -i "%EJEMPLOS%\empty_sample.py"
call :verificar 3

call :titulo "6. ERROR - formato no soportado  (se espera 3)"
python "%SCRIPT%" -i "%EJEMPLOS%\unsupported_sample.pdf"
call :verificar 3

call :titulo "7. ERROR - codigo Python con error de sintaxis  (se espera 3)"
python "%SCRIPT%" -i "%EJEMPLOS%\broken_syntax_sample.py"
call :verificar 3

call :titulo "8. ERROR - plantilla de assets ausente  (se espera 4)"
python "%SCRIPT%" -i "%EJEMPLOS%\input_sample.py" -o "%SALIDA%\demo_tarjetas.md" --template "%RAIZ%\assets\no_existe.md"
call :verificar 4

call :titulo "9. ERROR - carpeta sin formatos soportados  (se espera 3)"
if not exist "%SALIDA%\carpeta_vacia" mkdir "%SALIDA%\carpeta_vacia"
echo sin formatos soportados> "%SALIDA%\carpeta_vacia\notas.pdf"
python "%SCRIPT%" -i "%SALIDA%\carpeta_vacia"
call :verificar 3

call :titulo "9b. ERROR - uso incorrecto: --max-cards negativo  (se espera 2)"
python "%SCRIPT%" -i "%EJEMPLOS%\input_sample.py" --max-cards -1
call :verificar 2

call :titulo "10. Suite de pruebas automatizadas (36 casos)"
python -m unittest discover -s "%RAIZ%\tests"
call :verificar 0

call :titulo "11. Recorrido de una carpeta completa (caso mixto)"
python "%SCRIPT%" -i "%EJEMPLOS%" -r -o "%SALIDA%\demo_carpeta.md" --max-cards 20
call :verificar 0

call :titulo "Archivos generados"
dir /b "%SALIDA%\demo_*"
echo.
echo ==========================================================================
if %FALLOS%==0 (
  echo  DEMO COMPLETADA: %TOTAL% de %TOTAL% pasos con el codigo de salida esperado.
) else (
  echo  DEMO CON PROBLEMAS: %FALLOS% de %TOTAL% pasos con un codigo inesperado.
)
echo ==========================================================================
exit /b 0

REM ---------------------------------------------------------------------------
:titulo
echo.
echo ==========================================================================
echo  %~1
echo ==========================================================================
exit /b 0

REM ---------------------------------------------------------------------------
:verificar
set "ACTUAL=%ERRORLEVEL%"
set /a TOTAL+=1
if "%ACTUAL%"=="%~1" (
  echo   [OK] codigo de salida %ACTUAL% - esperado %~1
) else (
  set /a FALLOS+=1
  echo   [FALLO] codigo de salida %ACTUAL% - se esperaba %~1
)
exit /b 0
