#!/usr/bin/env python3
"""Code Study & Flashcards Generator: de codigo o apuntes a tarjetas de repaso activo.

Genera un archivo Markdown con tarjetas de estudio (pregunta, respuesta,
explicacion y el codigo original) a partir de un archivo de codigo o de notas de
estudio. El diseno de las preguntas no esta hardcodeado: se lee de
`references/active_recall_guide.md` y el formato sale de
`assets/flashcard_template.md`.

Uso minimo:

    python scripts/generate_cards.py -i examples/input_sample.py -o output/tarjetas.md

Codigos de salida: 0 ok, 2 uso incorrecto, 3 problema de entrada, 4 problema de
assets o referencias, 1 error inesperado. No hay dependencias externas: solo la
libreria estandar de Python 3.9 o superior.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

RAIZ_SCRIPT = Path(__file__).resolve().parent
if str(RAIZ_SCRIPT) not in sys.path:
    sys.path.insert(0, str(RAIZ_SCRIPT))

from flashcards_core import (  # noqa: E402
    GUIA_POR_DEFECTO,
    PLANTILLA_POR_DEFECTO,
    Guia,
    InputNotFoundError,
    NoCardsFoundError,
    SALIDA_ENTRADA,
    SALIDA_INESPERADA,
    SALIDA_OK,
    SkillError,
    Tarjeta,
    UsageError,
    cargar_guia,
    cargar_plantilla,
    escribir_salida,
    fecha_hoy,
    render_anki,
    render_markdown,
    ruta_legible,
    VERSION,
)
from flashcards_extract import (  # noqa: E402
    FuenteAnalizada,
    analizar_fuente,
    recopilar_archivos,
)

LENGUAJES_FORZABLES = (
    "auto",
    "py",
    "js",
    "jsx",
    "ts",
    "tsx",
    "java",
    "c",
    "cpp",
    "cs",
    "php",
    "go",
    "rb",
    "rs",
    "swift",
    "kt",
    "scala",
    "sql",
    "text",
)
FORMATO_SALIDA = {"md": ".md", "anki": ".txt"}


def construir_parser() -> argparse.ArgumentParser:
    """Define la linea de comandos de la skill."""
    parser = argparse.ArgumentParser(
        prog="generate_cards.py",
        description=(
            "Genera tarjetas de repaso activo (Active Recall) en Markdown a partir de "
            "un archivo de codigo o de notas de estudio."
        ),
        epilog=(
            "Ejemplos:\n"
            "  python scripts/generate_cards.py -i examples/input_sample.py -o output/tarjetas.md\n"
            "  python scripts/generate_cards.py -i examples/notas_sample.md --format anki -o output/tarjetas.txt\n"
            "  python scripts/generate_cards.py -i src/ -r --max-cards 40\n"
            "\n"
            "La plantilla y la guia se resuelven respecto a esta skill, no al directorio actual.\n"
            "Codigos de salida: 0 ok, 2 uso, 3 entrada, 4 assets/referencias, 1 inesperado.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        metavar="RUTA",
        help="Archivo de codigo o de notas a analizar (o carpeta, con -r para subcarpetas).",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="RUTA",
        help="Archivo de salida. Por defecto se escribe en el directorio actual.",
    )
    parser.add_argument(
        "--format",
        dest="formato",
        choices=("md", "anki"),
        default="md",
        help="md = Markdown con la plantilla de assets/ (por defecto). anki = TSV para importar en Anki.",
    )
    parser.add_argument(
        "--template",
        metavar="RUTA",
        default=str(PLANTILLA_POR_DEFECTO),
        help=f"Plantilla Markdown a rellenar (por defecto: {PLANTILLA_POR_DEFECTO}).",
    )
    parser.add_argument(
        "--guide",
        metavar="RUTA",
        default=str(GUIA_POR_DEFECTO),
        help=f"Guia de Active Recall con las reglas (por defecto: {GUIA_POR_DEFECTO}).",
    )
    parser.add_argument(
        "--lang",
        default="auto",
        choices=LENGUAJES_FORZABLES,
        help="Fuerza el analizador en vez de deducirlo de la extension.",
    )
    parser.add_argument(
        "--max-cards",
        dest="max_cards",
        type=int,
        default=0,
        metavar="N",
        help="Recorta el resultado a N tarjetas (0 = sin limite). Util para sesiones cortas.",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Si -i es una carpeta, incluir subcarpetas (ignora node_modules, dist, .git...).",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="No imprime el resumen por stdout.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Incluye el traceback completo cuando hay un error controlado.",
    )
    parser.add_argument("--version", action="version", version=f"code-study-flashcards {VERSION}")
    return parser


def ruta_salida_por_defecto(entrada: Path, formato: str) -> Path:
    """Nombre de salida automatico cuando el usuario no pasa -o."""
    base = entrada.name if entrada.is_dir() else entrada.stem
    return Path.cwd() / f"{base}_flashcards{FORMATO_SALIDA[formato]}"


def plural_tarjetas(cantidad: int) -> str:
    """Concordancia de 'tarjeta/tarjetas' en el informe de la terminal."""
    return "tarjeta" if cantidad == 1 else "tarjetas"


def tarjetas_por_tipo(tarjetas: Sequence[Tarjeta]) -> Dict[str, int]:
    """Conteo de tarjetas agrupadas por tipo, de mayor a menor."""
    conteo: Dict[str, int] = {}
    for tarjeta in tarjetas:
        conteo[tarjeta.tipo_clave] = conteo.get(tarjeta.tipo_clave, 0) + 1
    return dict(sorted(conteo.items(), key=lambda par: (-par[1], par[0])))


def reglas_usadas(tarjetas: Sequence[Tarjeta], guia: Guia) -> str:
    """Ids de reglas que aparecen en las tarjetas generadas."""
    usadas = {regla for tarjeta in tarjetas for regla in tarjeta.reglas}
    if not usadas:
        return guia.resumen_reglas()
    nombres = []
    for identificador in sorted(usadas):
        regla = guia.reglas.get(identificador)
        nombres.append(regla.citar() if regla else identificador)
    return ", ".join(nombres)


def construir_metadatos(entrada: Path, fuentes: Sequence[FuenteAnalizada], tarjetas: Sequence[Tarjeta], guia: Guia) -> Dict[str, Any]:
    """Tokens globales que la plantilla necesita en la cabecera."""
    origenes = [fuente.etiqueta for fuente in fuentes]
    titulo = (
        f"Repaso activo de {entrada.name} ({len(fuentes)} archivo/s)"
        if entrada.is_dir()
        else f"Repaso activo de {entrada.name}"
    )
    return {
        "TITULO": titulo,
        "ORIGEN": ", ".join(origenes),
        "ORIGENES": origenes,
        "LENGUAJE": ", ".join(sorted({fuente.lenguaje for fuente in fuentes})),
        "FECHA": fecha_hoy(),
        "REGLAS": reglas_usadas(tarjetas, guia),
        "TOTAL": len(tarjetas),
        "VERSION_SKILL": VERSION,
    }


def procesar(entrada: Path, guia: Guia, lenguaje: str, recursivo: bool) -> Tuple[List[FuenteAnalizada], List[str]]:
    """Analiza el archivo o la carpeta indicada y devuelve fuentes y avisos."""
    avisos: List[str] = []
    if not entrada.exists():
        raise InputNotFoundError(
            f"La entrada '{entrada}' no existe.",
            pista="Revisa la ruta pasada a -i/--input; se resuelve desde el directorio actual.",
        )
    if entrada.is_dir():
        archivos = recopilar_archivos(entrada, recursivo)
        if not archivos:
            raise InputNotFoundError(
                f"La carpeta '{entrada}' no contiene archivos con formato soportado.",
                pista=(
                    "Formatos aceptados: .py .js .jsx .ts .tsx .java .c .cpp .cs .php .go .rb .rs "
                    ".kt .swift .scala .sql .md .txt .rst. Usa -r para incluir subcarpetas."
                ),
            )
        fuentes: List[FuenteAnalizada] = []
        for archivo in archivos:
            try:
                fuentes.append(analizar_fuente(archivo, guia, lenguaje))
            except SkillError as exc:
                detalle = exc.mensaje.replace(str(archivo), "").replace(archivo.name, "")
                avisos.append(f"omitido {archivo.name}: {detalle.strip(chr(32) + chr(39) + chr(34))}")
        if not fuentes:
            raise InputNotFoundError(
                f"Ningun archivo de '{entrada}' pudo procesarse.",
                pista="; ".join(avisos[:3]) or "Revisa los archivos de la carpeta.",
            )
        return fuentes, avisos
    return [analizar_fuente(entrada, guia, lenguaje)], avisos


def imprimir_resumen(
    fuentes: Sequence[FuenteAnalizada],
    tarjetas: Sequence[Tarjeta],
    destino: Path,
    formato: str,
    guia: Guia,
    avisos: Sequence[str],
) -> None:
    """Muestra el informe de ejecucion que el estudiante ve en la terminal."""
    ancho = 64
    participio = "generada" if len(tarjetas) == 1 else "generadas"
    print("-" * ancho)
    print(
        f" code-study-flashcards {VERSION}  |  {len(tarjetas)} "
        f"{plural_tarjetas(len(tarjetas))} {participio}"
    )
    print("-" * ancho)
    for fuente in fuentes:
        tamano = fuente.ruta.stat().st_size
        print(
            f" Entrada   {fuente.etiqueta} "
            f"({fuente.lenguaje}, {tamano / 1024:.1f} KB, "
            f"{len(fuente.tarjetas)} {plural_tarjetas(len(fuente.tarjetas))})"
        )
    for tipo, cantidad in tarjetas_por_tipo(tarjetas).items():
        etiqueta = guia.tipos.get(tipo)
        nombre = etiqueta.etiqueta if etiqueta else tipo
        print(f"   - {cantidad:>3}  {nombre} ({tipo})")
    print(f" Reglas    {reglas_usadas(tarjetas, guia)}")
    if avisos:
        print(" Avisos")
        for aviso in avisos:
            print(f"   ! {aviso}")
    print(f" Salida    {ruta_legible(destino)}")
    print("-" * ancho)
    if formato == "anki":
        print(" Para importar en Anki: Archivo > Importar > tipo 'texto separado por tabuladores'.")
    else:
        print(" Siguiente paso: responde cada tarjeta SIN leer la respuesta; despues compara.")


def ejecutar(args: argparse.Namespace) -> int:
    """Flujo completo: cargar assets, analizar entrada, renderizar y escribir."""
    if args.max_cards < 0:
        raise UsageError(
            "--max-cards no puede ser negativo.",
            pista="Usa 0 para no limitar el numero de tarjetas.",
        )
    guia = cargar_guia(Path(args.guide))
    plantilla = cargar_plantilla(Path(args.template)) if args.formato == "md" else ""

    entrada = Path(args.input)
    fuentes, avisos = procesar(entrada, guia, args.lang, args.recursive)
    for fuente in fuentes:
        avisos.extend(f"{fuente.nombre}: {aviso}" for aviso in fuente.avisos)

    tarjetas: List[Tarjeta] = [tarjeta for fuente in fuentes for tarjeta in fuente.tarjetas]
    if not tarjetas:
        raise NoCardsFoundError(
            f"'{entrada.name}' se leyo correctamente pero no genero ninguna tarjeta.",
            pista=(
                "El archivo no tiene funciones, clases, constantes, secciones ni listas reconocibles. "
                "Prueba con otro archivo o revisa que tenga contenido de estudio."
            ),
        )
    if args.max_cards and len(tarjetas) > args.max_cards:
        avisos.append(
            f"recortado de {len(tarjetas)} a {args.max_cards} tarjetas por --max-cards "
            f"(las primeras {args.max_cards} en orden de aparicion)."
        )
        tarjetas = tarjetas[: args.max_cards]

    metadatos = construir_metadatos(entrada, fuentes, tarjetas, guia)
    if args.formato == "md":
        contenido = render_markdown(plantilla, tarjetas, metadatos)
        destino = Path(args.output) if args.output else ruta_salida_por_defecto(entrada, args.formato)
    else:
        contenido = render_anki(tarjetas, guia)
        destino = Path(args.output) if args.output else ruta_salida_por_defecto(entrada, args.formato)
    escribir_salida(destino, contenido)

    if not args.quiet:
        imprimir_resumen(fuentes, tarjetas, destino, args.formato, guia, avisos)
    return SALIDA_OK


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Punto de entrada: parsea argumentos y traduce errores a codigos de salida."""
    parser = construir_parser()
    args = parser.parse_args(argv)
    try:
        return ejecutar(args)
    except SkillError as exc:
        print(exc.render(), file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        return exc.exit_code
    except KeyboardInterrupt:
        print("\n[ERROR] Interrumpido por el usuario (Ctrl+C).", file=sys.stderr)
        return 130
    except OSError as exc:
        print(f"[ERROR] Fallo del sistema: {exc}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        return SALIDA_ENTRADA
    except Exception as exc:  # pragma: no cover - red de seguridad
        print(f"[ERROR] Fallo inesperado: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("  Sugerencia: ejecuta con --verbose y reporta el traceback completo.", file=sys.stderr)
        traceback.print_exc()
        return SALIDA_INESPERADA


if __name__ == "__main__":
    sys.exit(main())
