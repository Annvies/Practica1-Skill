---
name: code-study-flashcards
description: Convierte codigo fuente o apuntes de estudio en tarjetas de repaso activo (Active Recall) en Markdown o TSV para Anki, usando reglas pedagogicas explicitas y trazables. Usar cuando el usuario pida repasar,ortal flashcards, Practice Quiz, question cards, flashcards de codigo, tarjetas de estudio, quiz de codigo, active recall, o cuando quiera transformar un archivo .py/.js/.ts/.java/.c/.cpp/.cs/.php/.go/.rb/.rs o apuntes .md/.txt en preguntas de repaso.
license: MIT
---

# code-study-flashcards

Genera tarjetas de repaso activo desde codigo o apuntes. Cada tarjeta es una
**pregunta que obliga a producir la respuesta antes de poder leerla**, con la
explicacion minima y el codigo original plegado para verificar.

## Cuando usar esta skill

- "Repasemos este archivo con flashcards" / "quiero tarjetas de este codigo"
- "Convierte mis apuntes en preguntas de repaso"
- "Sacame un quiz de este modulo" / "preparame para el parcial"
- "Exporta esto a Anki"
- "Marca los huecos de este codigo sin documentar"

## Cuando NO usar esta skill

- El usuario quiere **resumir** o **explicar** el codigo (sin preguntas).
- El usuario quiere **refactorizar**, corregir bugs o escribir codigo nuevo.
- El codigo es pseudocodigo o texto sin estructura: en ese caso conviene
  convertirlo a `.md`/`.txt` y usar `--lang text`.

## Requisitos

- Python 3.9 o superior. **Cero dependencias externas**: solo libreria estandar.
- Offline: no hace llamadas de red, no pide API keys, no escribe fuera de la
  ruta de salida indicada.

## Uso

Desde la carpeta de la skill (o con la ruta completa al script):

```bash
python scripts/generate_cards.py -i examples/input_sample.py -o output/tarjetas.md
```

```bash
# Apuntes, recortado a 10 tarjetas para una sesion corta
python scripts/generate_cards.py -i notas/tema3.md -o output/tema3.md --max-cards 10

# Export a Anki (TSV: anverso<TAB>reverso)
python scripts/generate_cards.py -i src/inventario.py --format anki -o output/inventario.txt

# Carpeta completa, con subcarpetas
python scripts/generate_cards.py -i src/ -r --max-cards 40
```

Demostracion completa (casos exitosos + matriz de errores):

```bash
scripts\demo.bat     # Windows
bash scripts/demo.sh  # Linux, macOS o Git Bash
```

### Opciones

| Opcion | Efecto |
| --- | --- |
| `-i, --input` | Archivo o carpeta a analizar. **Obligatorio.** |
| `-o, --output` | Ruta de salida. Por defecto, `<nombre>_flashcards.md` en el directorio actual. |
| `--format` | `md` (Markdown, por defecto) o `anki` (TSV separado por tabuladores). |
| `--template` | Plantilla alternativa. Por defecto `assets/flashcard_template.md`. |
| `--guide` | Guia alternativa. Por defecto `references/active_recall_guide.md`. |
| `--lang` | Fuerza el analizador: `py`, `js`, `ts`, `java`, `c`, `cpp`, `cs`, `php`, `go`, `rb`, `rs`, `swift`, `kt`, `scala`, `sql`, `text`. Por defecto se deduce de la extension. |
| `--max-cards N` | Recorta a N tarjetas (`0` = sin limite). Para sesiones de 10 minutos. |
| `-r, --recursive` | Al pasar una carpeta, incluye subcarpetas (ignora `.git`, `node_modules`, `dist`, `venv`). |
| `-q, --quiet` | Suprime el resumen por stdout. |
| `--verbose` | Anade el traceback a los errores controlados. |

## Formatos soportados

- **Codigo**: `.py` (AST real), `.js .jsx .mjs .cjs .ts .tsx`, `.java`, `.c .h`, `.cc .cpp .hpp`,
  `.cs`, `.php`, `.go`, `.rb`, `.rs`, `.kt`, `.swift`, `.scala`, `.sql` (heuristico por lineas).
- **Apuntes**: `.md`, `.markdown`, `.txt`, `.rst` (secciones, listas, terminos y bloques de codigo).

Un archivo con extension no soportada se rechaza con una explicacion de como
forzar el analizador. Un `.pdf` no se procesa: el skill no extrae texto de
binarios.

## Que genera

Cada tarjeta trae tipo, dificultad, tags, ubicacion, la pregunta, la respuesta
minima, la explicacion, un fragmento de codigo y el codigo original en un
`<details>` plegable. Ademas anade un comentario HTML con las reglas aplicadas
(R8: auditable), para que siempre se pueda responder *"¿por que esta pregunta?"*.

Tipos: proposito de funcion, parametros, valor de retorno, flujo de control,
constante de modulo, constructor, atributos de clase, metodos publicos,
hueco de documentacion (gap card), seccion y lista de apuntes, y codigo
embebido en notas.

Las reglas R1 a R8 estan en `references/active_recall_guide.md` y se leen en
tiempo de ejecucion: la guia gobierna el generador, no es decorativa.

## Como se usa (flujo recomendado)

1. Preguntar por el formato: un archivo o la carpeta del proyecto.
2. Elegir el alcance: todas las tarjetas o `--max-cards` para una sesion corta.
3. Ejecutar el generador y leer el resumen de la terminal.
4. Entregar el archivo .md; si el usuario usa Anki, ofrecer `--format anki`.
5. Recordar la sesion: responder **antes** de desplegar, fallar esta bien, y
   repasar las falladas a las 48 h.

## Manejo de errores

| Codigo | Situacion | Que hacer |
| --- | --- | --- |
| 0 | Generacion correcta | Entregar la salida. |
| 2 | Uso incorrecto (por ejemplo `--max-cards -1`, o falta `-i`). | Corregir el comando; el mensaje dice cual. |
| 3 | Problema de entrada: no existe, vacia, ilegible, sin extension valida, codigo con error de sintaxis, o carpeta sin archivos soportados. | Revisar el archivo o usar `--lang`. |
| 4 | Faltan o son invalidos `assets/flashcard_template.md` o `references/active_recall_guide.md`. | Reinstalar la skill: revisar el clon. |
| 1 | Error inesperado. | Reintentar con `--verbose` y reportar el traceback. |

En una carpeta, un archivo problematico no aborta la corrida: se omite con un
aviso y el resto se procesa. Solo si **ningun** archivo sirve, el codigo es 3.

Ante un error de sintaxis, la sugerencia por defecto es correcta: si el archivo
es pseudocodigo, renombrarlo a `.md`/`.txt` o usar `--lang text`.

## Estructura

```
code-study-flashcards/
├── SKILL.md
├── assets/flashcard_template.md      # plantilla Markdown con marcadores
├── references/active_recall_guide.md  # reglas R1-R8 + JSON machine-readable
├── scripts/
│   ├── generate_cards.py   # CLI, orquestacion, resumen y export Anki
│   ├── flashcards_core.py   # errores, carga de assets, render Markdown/Anki
│   ├── flashcards_extract.py# extractores: AST Python, heuristico, apuntes
│   ├── demo.bat            # demostracion en Windows
│   └── demo.sh             # demostracion en Linux/macOS/Git Bash
├── examples/               # casos exitosos, de error y expected_output.md
├── docs/capturas/         # 01 a 06, evidencia de la presentacion
└── tests/test_generate_cards.py
```

## Pruebas

```bash
python -m unittest discover -s tests
```

36 casos, sin dependencias. Cubren generacion, extractores, Anki, determinismo,
carga de assets y los cinco codigos de salida.
