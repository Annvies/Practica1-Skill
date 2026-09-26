"""Code Study & Flashcards Generator - extractores por lenguaje.

Cada clase `Analizador*` recibe el texto de una entrada, la guia pedagogica ya
validada y produce una lista de `Tarjeta`. El despacho por extension vive en
`analizar_fuente`, que tambien resuelve la lectura y los errores de entrada.

Estrategia por lenguaje:

- `.py`  -> modulo `ast` de la libreria estandar: firmas, anotaciones,
            docstrings, returns, clases, constantes, imports y flujo de control.
- resto de codigo (js/ts/java/c/...) -> parser heuristico por lineas, porque
            no existe un AST estandar en la stdlib. Es una degradacion
            consciente: funciona sin dependencias, pero la guia se marca como
            heuristica en la tarjeta.
- `.md`/`.txt` -> apuntes: secciones, terminos en negrita, listas y bloques de
            codigo embebidos (que se delegan al analizador del lenguaje).
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from flashcards_core import (
    CodeParseError,
    DecodingError,
    EmptyInputError,
    Guia,
    InputNotFoundError,
    LecturaError,
    Tarjeta,
    UnsupportedFormatError,
    pertenece_a,
    recortar,
    ruta_legible,
)

LIMITE_TARJETAS_POR_BLOQUE = 4
MAX_TERMINOS_POR_ARCHIVO = 6
MAX_LISTAS_POR_ARCHIVO = 6
MAX_LINEAS_FRAGMENTO = 14
MAX_LINEAS_COMPLETO = 60
MAX_LONGITUD_LISTADO = 6

LENGUAJES_CODIGO = {
    ".py": "py",
    ".js": "js",
    ".mjs": "js",
    ".cjs": "js",
    ".jsx": "jsx",
    ".ts": "ts",
    ".tsx": "tsx",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cs": "cs",
    ".php": "php",
    ".go": "go",
    ".rb": "rb",
    ".rs": "rs",
    ".swift": "swift",
    ".kt": "kt",
    ".scala": "scala",
    ".sql": "sql",
}

LENGUAJES_NOTAS = {
    ".md": "md",
    ".markdown": "md",
    ".txt": "txt",
    ".rst": "md",
}

CERCA_FENCE = re.compile(r"^```+\s*([A-Za-z0-9_+-]*)\s*$")
ALIAS_CERCA_FENCE = {
    "python": "py",
    "py": "py",
    "javascript": "js",
    "js": "js",
    "jsx": "jsx",
    "typescript": "ts",
    "ts": "ts",
    "tsx": "tsx",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "c++": "cpp",
    "csharp": "cs",
    "cs": "cs",
    "php": "php",
    "go": "go",
    "ruby": "rb",
    "rb": "rb",
    "rust": "rs",
    "rs": "rs",
    "sql": "sql",
    "bash": "sh",
    "sh": "sh",
    "text": "text",
    "txt": "text",
    "": "text",
}

NOMBRE_LENGUAJE = {
    "py": "python",
    "js": "javascript",
    "jsx": "jsx",
    "ts": "typescript",
    "tsx": "tsx",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "cs": "csharp",
    "php": "php",
    "go": "go",
    "rb": "ruby",
    "rs": "rust",
    "swift": "swift",
    "kt": "kotlin",
    "scala": "scala",
    "sql": "sql",
    "md": "text",
    "txt": "text",
    "text": "text",
    "sh": "bash",
}

DIRECCIONES_IGNORAR = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".venv",
    "venv",
    "env",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    ".next",
    "target",
    "vendor",
    "coverage",
    "site-packages",
    "generated",
}

# Archivos que no contienen implementacion propia: solo declaraciones de tipos.
ARCHIVOS_IGNORAR = (".d.ts",)


@dataclass
class FuenteAnalizada:
    """Resultado de procesar una entrada: sus tarjetas y los avisos del proceso."""

    ruta: Path
    etiqueta: str
    lenguaje: str
    tarjetas: List[Tarjeta] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)

    @property
    def nombre(self) -> str:
        return self.ruta.name

    def conteo_por_tipo(self) -> Dict[str, int]:
        conteo: Dict[str, int] = {}
        for tarjeta in self.tarjetas:
            conteo[tarjeta.tipo_clave] = conteo.get(tarjeta.tipo_clave, 0) + 1
        return dict(sorted(conteo.items(), key=lambda par: (-par[1], par[0])))


# --------------------------------------------------------------------------
# Lectura y despacho
# --------------------------------------------------------------------------
def es_formato_soportado(ruta: Path) -> bool:
    return ruta.suffix.lower() in LENGUAJES_CODIGO or ruta.suffix.lower() in LENGUAJES_NOTAS


def formatos_soportados() -> str:
    codigo = sorted(LENGUAJES_CODIGO)
    notas = sorted(LENGUAJES_NOTAS)
    return (
        f"codigo: {', '.join(codigo)}\n"
        f"notas : {', '.join(notas)}\n"
        f"otros : usa --lang py|js|ts|java|c|cpp|cs|php|go|rb|rs|sql|text para forzar el analisis"
    )


def leer_texto(ruta: Path) -> str:
    """Lee un archivo de entrada validando vacio, binario y decodificacion."""
    if not ruta.exists():
        raise InputNotFoundError(
            f"El archivo '{ruta}' no existe.",
            pista="Revisa la ruta con -i/--input; las rutas relativas se resuelven desde donde ejecutes el script.",
        )
    if ruta.is_dir():
        raise InputNotFoundError(
            f"'{ruta}' es una carpeta, no un archivo.",
            pista="Pasa la carpeta directamente: el script recorre los formatos soportados (usa -r para incluir subcarpetas).",
        )
    try:
        datos = ruta.read_bytes()
    except OSError as exc:
        raise LecturaError(
            f"No se pude leer '{ruta}': {exc.strerror or exc}",
            pista="Comprueba los permisos del archivo o que no este abierto por otro programa.",
        )
    if not datos.strip():
        raise EmptyInputError(
            f"El archivo '{ruta}' esta vacio (0 bytes utiles).",
            pista="Un archivo vacio no tiene conceptos que revisar: aniade codigo o notas y vuelve a intentarlo.",
        )
    muestra = datos[:8192]
    if b"\x00" in muestra or muestra[:4] in (b"\x7fELF", b"PK\x03\x04", b"\xd0\xcf\x11\xe0"):
        raise DecodingError(
            f"'{ruta.name}' es un archivo binario, no texto.",
            pista="Esta skill procesa codigo fuente y notas en texto plano (.py, .js, .md, .txt, ...).",
        )
    for codificacion in ("utf-8", "cp1252", "latin-1"):
        try:
            texto = datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
        if texto.startswith("\ufeff"):
            texto = texto[1:]
        return texto
    raise DecodingError(
        f"'{ruta.name}' usa una codificacion que no se pudo decodificar.",
        pista="Reexporta el archivo como UTF-8 y vuelve a ejecutar el script.",
    )


def resolver_lenguaje(ruta: Path, forzado: str) -> str:
    """Devuelve el identificador de lenguaje segun --lang o la extension."""
    if forzado and forzado != "auto":
        if forzado == "text":
            return "text"
        return forzado
    extension = ruta.suffix.lower()
    if extension in LENGUAJES_CODIGO:
        return LENGUAJES_CODIGO[extension]
    if extension in LENGUAJES_NOTAS:
        return LENGUAJES_NOTAS[extension]
    raise UnsupportedFormatError(
        f"Formato no soportado para '{ruta.name}' (extension '{extension or 'sin extension'}').",
        pista=formatos_soportados(),
    )


def construir_analizador(
    lenguaje: str, texto: str, etiqueta: str, guia: Guia, nombre: str
) -> Any:
    if lenguaje == "py":
        return AnalizadorPython(texto, etiqueta, guia, nombre)
    if lenguaje in ("md", "txt"):
        return AnalizadorNotas(texto, etiqueta, guia, nombre)
    return AnalizadorBloques(texto, etiqueta, guia, nombre, lenguaje)


def analizar_fuente(ruta: Path, guia: Guia, lenguaje_forzado: str = "auto") -> FuenteAnalizada:
    """Procesa una entrada completa: validacion, lectura, analisis y tarjetas."""
    lenguaje = resolver_lenguaje(ruta, lenguaje_forzado)
    texto = leer_texto(ruta)
    etiqueta = ruta_legible(ruta)
    analizador = construir_analizador(lenguaje, texto, etiqueta, guia, ruta.name)
    tarjetas = list(analizador.tarjetas())
    avisos = list(getattr(analizador, "avisos", []))
    if not tarjetas:
        avisos.append(
            f"'{ruta.name}' no contiene funciones, clases, constantes ni secciones reconocibles."
        )
    return FuenteAnalizada(
        ruta=ruta, etiqueta=etiqueta, lenguaje=lenguaje, tarjetas=tarjetas, avisos=avisos
    )


def recopilar_archivos(raiz: Path, recursivo: bool) -> List[Path]:
    """Lista los archivos con formato soportado de una carpeta, sin ruido comun."""
    encontrados: List[Path] = []
    patron = raiz.rglob("*") if recursivo else raiz.glob("*")
    for candidato in sorted(patron):
        if not candidato.is_file() or not es_formato_soportado(candidato):
            continue
        if candidato.name.endswith(ARCHIVOS_IGNORAR):
            continue
        partes = set(candidato.relative_to(raiz).parts[:-1])
        if partes & DIRECCIONES_IGNORAR or candidato.name.startswith("."):
            continue
        encontrados.append(candidato)
    return encontrados


# --------------------------------------------------------------------------
# Python (ast)
# --------------------------------------------------------------------------
class AnalizadorPython:
    """Extractor de tarjetas a partir del AST de un modulo Python."""

    def __init__(self, texto: str, etiqueta: str, guia: Guia, nombre: str) -> None:
        self.lineas = texto.splitlines()
        self.etiqueta = etiqueta
        self.guia = guia
        self.nombre = nombre
        self.avisos: List[str] = []
        self.arbol = self._parsear(texto)

    def _parsear(self, texto: str) -> ast.Module:
        try:
            return ast.parse(texto)
        except SyntaxError as exc:
            raise CodeParseError(
                f"'{self.nombre}' no es Python valido (linea {exc.lineno}): {exc.msg}",
                pista=(
                    "Corrige el error de sintaxis. Si el archivo es pseudocodigo o texto plano, "
                    "renombralo a .md/.txt o ejecuta con --lang text."
                ),
            ) from exc

    def tarjetas(self) -> List[Tarjeta]:
        resultado: List[Tarjeta] = []
        imports: List[str] = []
        for nodo in self.arbol.body:
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                resultado.extend(self._funcion(nodo, clase=""))
            elif isinstance(nodo, ast.ClassDef):
                resultado.extend(self._clase(nodo))
            elif isinstance(nodo, (ast.Import, ast.ImportFrom)):
                imports.extend(self._imports(nodo))
            elif isinstance(nodo, (ast.Assign, ast.AnnAssign)):
                resultado.extend(self._constante(nodo))
            elif isinstance(nodo, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                if not self._es_guard_main(nodo):
                    resultado.append(self._flujo_modulo(nodo))
            elif isinstance(nodo, ast.Expr) and isinstance(nodo.value, ast.Constant):
                continue
        if imports:
            resultado.append(self._tarjeta_imports(imports))
        return resultado

    def _es_guard_main(self, nodo: ast.AST) -> bool:
        if not isinstance(nodo, ast.If):
            return False
        prueba = nodo.test
        if not isinstance(prueba, ast.Compare):
            return False
        if not isinstance(prueba.left, ast.Name) or prueba.left.id != "__name__":
            return False
        return any(
            isinstance(comparador, ast.Constant) and comparador.value == "__main__"
            for comparador in prueba.comparators
        )

    def _ubicar(self, nodo: ast.AST) -> str:
        return f"{self.etiqueta}:{getattr(nodo, 'lineno', 1)}"

    def _fragmento(self, inicio: int, fin: Optional[int], limite: int) -> str:
        if inicio < 1 or inicio > len(self.lineas):
            return ""
        ultimo = min(fin or len(self.lineas), len(self.lineas))
        seleccion = self.lineas[inicio - 1 : ultimo]
        if len(seleccion) > limite:
            seleccion = seleccion[:limite] + [f"... (+{ultimo - inicio + 1 - limite} lineas)"]
        return "\n".join(seleccion)

    def _unparse(self, nodo: Optional[ast.AST]) -> str:
        if nodo is None:
            return ""
        try:
            return ast.unparse(nodo)
        except Exception:
            return "<expresion>"

    def _firma(self, nodo: ast.AST) -> str:
        argumentos = nodo.args
        solo_posicionales = list(getattr(argumentos, "posonlyargs", []) or [])
        posicionales = list(argumentos.args)
        todos = solo_posicionales + posicionales
        valores_por_defecto = [None] * (len(todos) - len(argumentos.defaults)) + list(
            argumentos.defaults
        )
        partes: List[str] = []
        for indice, argumento in enumerate(todos):
            piezas = argumento.arg
            if argumento.annotation is not None:
                piezas += ": " + self._unparse(argumento.annotation)
            defecto = valores_por_defecto[indice] if indice < len(valores_por_defecto) else None
            if defecto is not None:
                piezas += (" = " if argumento.annotation is not None else "=") + self._unparse(defecto)
            partes.append(piezas)
        if solo_posicionales:
            partes.append("/")
        if argumentos.vararg is not None:
            piezas = "*" + argumentos.vararg.arg
            if argumentos.vararg.annotation is not None:
                piezas += ": " + self._unparse(argumentos.vararg.annotation)
            partes.append(piezas)
        elif argumentos.kwonlyargs:
            partes.append("*")
        for argumento, defecto in zip(argumentos.kwonlyargs, argumentos.kw_defaults):
            piezas = argumento.arg
            if argumento.annotation is not None:
                piezas += ": " + self._unparse(argumento.annotation)
            if defecto is not None:
                piezas += (" = " if argumento.annotation is not None else "=") + self._unparse(defecto)
            partes.append(piezas)
        if argumentos.kwarg is not None:
            piezas = "**" + argumentos.kwarg.arg
            if argumentos.kwarg.annotation is not None:
                piezas += ": " + self._unparse(argumentos.kwarg.annotation)
            partes.append(piezas)
        firma = f"{nodo.name}({', '.join(partes)})"
        anotacion_retorno = getattr(nodo, "returns", None)
        if anotacion_retorno is not None:
            firma += f" -> {self._unparse(anotacion_retorno)}"
        if isinstance(nodo, ast.AsyncFunctionDef):
            firma = "async " + firma
        return firma

    def _parametros(self, nodo: ast.AST) -> List[Dict[str, Any]]:
        argumentos = nodo.args
        solo_posicionales = list(getattr(argumentos, "posonlyargs", []) or [])
        posicionales = list(argumentos.args)
        todos = solo_posicionales + posicionales
        valores_por_defecto = [None] * (len(todos) - len(argumentos.defaults)) + list(
            argumentos.defaults
        )
        resultado: List[Dict[str, Any]] = []
        for indice, argumento in enumerate(todos):
            defecto = valores_por_defecto[indice] if indice < len(valores_por_defecto) else None
            resultado.append(
                {
                    "nombre": argumento.arg,
                    "tipo": self._unparse(argumento.annotation) or "sin anotacion",
                    "defecto": self._unparse(defecto) if defecto is not None else None,
                    "variadico": False,
                }
            )
        if argumentos.vararg is not None:
            resultado.append(
                {
                    "nombre": "*" + argumentos.vararg.arg,
                    "tipo": self._unparse(argumentos.vararg.annotation) or "sin anotacion",
                    "defecto": None,
                    "variadico": True,
                }
            )
        for argumento, defecto in zip(argumentos.kwonlyargs, argumentos.kw_defaults):
            resultado.append(
                {
                    "nombre": argumento.arg,
                    "tipo": self._unparse(argumento.annotation) or "sin anotacion",
                    "defecto": self._unparse(defecto) if defecto is not None else None,
                    "variadico": False,
                }
            )
        if argumentos.kwarg is not None:
            resultado.append(
                {
                    "nombre": "**" + argumentos.kwarg.arg,
                    "tipo": self._unparse(argumentos.kwarg.annotation) or "sin anotacion",
                    "defecto": None,
                    "variadico": True,
                }
            )
        return resultado

    def _retornos(self, nodo: ast.AST) -> Tuple[List[str], bool]:
        valores: List[str] = []
        tiene_return_vacio = False
        for hijo in ast.walk(nodo):
            if isinstance(hijo, ast.Return):
                if hijo.value is None:
                    tiene_return_vacio = True
                else:
                    texto = self._unparse(hijo.value)
                    if texto not in valores:
                        valores.append(texto)
        return valores, tiene_return_vacio

    def _flujo(self, nodo: ast.AST) -> Dict[str, Any]:
        conteo: Dict[str, int] = {}
        for hijo in ast.walk(nodo):
            etiqueta = None
            if isinstance(hijo, ast.If):
                etiqueta = "if"
            elif isinstance(hijo, (ast.For, ast.AsyncFor)):
                etiqueta = "for"
            elif isinstance(hijo, ast.While):
                etiqueta = "while"
            elif isinstance(hijo, ast.Try):
                etiqueta = "try/except"
            elif isinstance(hijo, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                etiqueta = "comprension"
            elif isinstance(hijo, ast.BoolOp):
                etiqueta = "operador booleano"
            if etiqueta:
                conteo[etiqueta] = conteo.get(etiqueta, 0) + 1
        ramas = sum(
            valor
            for clave, valor in conteo.items()
            if clave in ("if", "for", "while", "try/except", "comprension")
        )
        descripcion = ", ".join(f"{clave} x{valor}" for clave, valor in sorted(conteo.items()))
        return {"conteo": conteo, "ramas": ramas, "descripcion": descripcion or "control lineal sin decisiones"}

    def _resumen_docstring(self, documentacion: str) -> str:
        """Se queda con la frase resumen y descarta las secciones Args/Returns."""
        frases: List[str] = []
        for linea in documentacion.splitlines():
            limpia = linea.strip()
            if not limpia:
                if frases:
                    break
                continue
            if re.match(
                r"^(Args|Arguments|Params|Parameters|Returns|Return|Raises|Yields|Examples?|Notes?)\s*:",
                limpia,
            ):
                break
            if limpia.startswith("@"):
                break
            frases.append(limpia)
        return " ".join(frases)

    def _funcion(self, nodo: ast.AST, clase: str = "") -> List[Tarjeta]:
        ambito = f"{clase}.{nodo.name}" if clase else nodo.name
        firma = self._firma(nodo)
        documentacion = ast.get_docstring(nodo)
        parametros = self._parametros(nodo)
        retornos, retorno_vacio = self._retornos(nodo)
        flujo = self._flujo(nodo)
        ubicacion = self._ubicar(nodo)
        fragmento = self._fragmento(nodo.lineno, getattr(nodo, "end_lineno", None), MAX_LINEAS_FRAGMENTO)
        completo = self._fragmento(nodo.lineno, getattr(nodo, "end_lineno", None), MAX_LINEAS_COMPLETO)
        complejidad = 1 + flujo["ramas"] + len(retornos)
        resultado: List[Tarjeta] = []

        if documentacion:
            resumen = recortar(self._resumen_docstring(documentacion), 260)
            lineas_doc = len(documentacion.splitlines())
            descripcion_retorno = (
                f"Devuelve {len(retornos)} forma(s) distinta(s): "
                + "; ".join(f"`{r}`" for r in retornos[:3])
                if retornos
                else "No tiene `return` con valor: su efecto es un efecto lateral."
            )
            resultado.append(
                self.guia.construir_tarjeta(
                    "funcion_proposito",
                    concepto=ambito,
                    respuesta=f"{resumen}\n\nFirma: `{firma}`",
                    explicacion=[
                        f"Firma completa: `{firma}`",
                        descripcion_retorno,
                        f"La docstring tiene {lineas_doc} lineas; la respuesta usa solo la frase resumen.",
                        f"Complejidad aproximada: {complejidad} (1 + ramas + returns).",
                        f"Ubicacion: {ubicacion}",
                    ],
                    codigo=fragmento,
                    codigo_completo=completo,
                    ubicacion=ubicacion,
                    archivo=self.etiqueta,
                    lenguaje="python",
                    complejidad=complejidad,
                    contexto_extra={"detalle": resumen},
                )
            )
        else:
            pistas = []
            if parametros:
                pistas.append(
                    "recibe " + ", ".join(f"`{p['nombre']}`" for p in parametros[:4])
                )
            if retornos:
                pistas.append("devuelve " + ", ".join(f"`{r}`" for r in retornos[:2]))
            if flujo["ramas"]:
                pistas.append(f"contiene {flujo['ramas']} decision(es) de control")
            resultado.append(
                self.guia.construir_tarjeta(
                    "funcion_sin_docstring",
                    concepto=ambito,
                    respuesta=(
                        "No hay respuesta en el codigo: esta es una *gap card* (regla R5). "
                        "Reconstruye la respuesta y despues comparala con la implementacion.\n\n"
                        f"Pistas del cuerpo: {'; '.join(pistas) if pistas else 'funcion sin cuerpo util'}."
                    ),
                    explicacion=[
                        "`ast.get_docstring` devuelve None: la funcion no esta documentada.",
                        f"Firma a reconstruir: `{firma}`",
                        f"Complejidad aproximada: {complejidad}.",
                        f"Ubicacion: {ubicacion}",
                    ],
                    codigo=fragmento,
                    codigo_completo=completo,
                    ubicacion=ubicacion,
                    archivo=self.etiqueta,
                    lenguaje="python",
                    complejidad=max(complejidad, 2),
                    tags_extra=["gap"],
                )
            )

        detalle_parametros = "; ".join(
            f"`{p['nombre']}`: {p['tipo']}"
            + (f" = {p['defecto']}" if p["defecto"] is not None else "")
            + (" (variadico)" if p["variadico"] else "")
            for p in parametros
        )
        instancia = bool(clase) and bool(parametros) and parametros[0]["nombre"] in ("self", "cls")
        utiles = parametros[1:] if instancia else parametros
        obligatorios = [p["nombre"] for p in utiles if p["defecto"] is None and not p["variadico"]]
        opcionales = [p["nombre"] for p in utiles if p["defecto"] is not None]
        lineas_parametros = [
            f"Total de parametros: {len(parametros)}"
            + (f" (contando `{parametros[0]['nombre']}`, que es la instancia de la clase)" if instancia else "."),
        ]
        if instancia:
            lineas_parametros.append(
                f"`{parametros[0]['nombre']}` lo inyecta Python: el estudiante no lo escribe al llamar."
            )
        lineas_parametros += [
            f"Obligatorios: {', '.join(obligatorios) if obligatorios else 'ninguno'}.",
            f"Con valor por defecto: {', '.join(opcionales) if opcionales else 'ninguno'}.",
            f"Firma completa: `{firma}`",
            f"Ubicacion: {ubicacion}",
        ]
        resultado.append(
            self.guia.construir_tarjeta(
                "funcion_parametros",
                concepto=ambito,
                respuesta=detalle_parametros or "La funcion no recibe parametros.",
                explicacion=lineas_parametros,
                codigo=fragmento,
                codigo_completo=completo,
                ubicacion=ubicacion,
                archivo=self.etiqueta,
                lenguaje="python",
                complejidad=complejidad,
                contexto_extra={"detalle": detalle_parametros},
            )
        )

        if retornos or retorno_vacio:
            resultado.append(
                self.guia.construir_tarjeta(
                    "funcion_retorno",
                    concepto=ambito,
                    respuesta=(
                        "; ".join(f"`{r}`" for r in retornos) or "solo `return` sin valor"
                    ),
                    explicacion=[
                        f"Puntos de retorno con valor: {len(retornos)}.",
                        *[f"Camino {indice}: devuelve `{valor}`." for indice, valor in enumerate(retornos[:MAX_LONGITUD_LISTADO], start=1)],
                        "Existe `return` sin valor: la funcion puede terminar sin resultado." if retorno_vacio else "Todos los `return` devuelven valor.",
                        f"Completitud: {'falta documentar' if not documentacion else 'documentada'}.",
                        f"Ubicacion: {ubicacion}",
                    ],
                    codigo=fragmento,
                    codigo_completo=completo,
                    ubicacion=ubicacion,
                    archivo=self.etiqueta,
                    lenguaje="python",
                    complejidad=complejidad,
                    contexto_extra={"detalle": "; ".join(retornos[:2])},
                )
            )

        if flujo["ramas"]:
            resultado.append(
                self.guia.construir_tarjeta(
                    "flujo_control",
                    concepto=ambito,
                    respuesta=f"Flujo de control: {flujo['descripcion']}.",
                    explicacion=[
                        f"Decisiones de control: {flujo['descripcion']}.",
                        f"Numero de ramas: {flujo['ramas']}.",
                        f"Complejidad aproximada: {complejidad}.",
                        f"Ubicacion: {ubicacion}",
                    ],
                    codigo=fragmento,
                    codigo_completo=completo,
                    ubicacion=ubicacion,
                    archivo=self.etiqueta,
                    lenguaje="python",
                    complejidad=complejidad + 1,
                    contexto_extra={"tipo": "funcion", "detalle": flujo["descripcion"]},
                )
            )
        return resultado

    def _atributos(self, nodo_clase: ast.ClassDef) -> List[Tuple[str, str, Optional[int]]]:
        atributos: List[Tuple[str, str, Optional[int]]] = []
        for hijo in nodo_clase.body:
            if isinstance(hijo, ast.AnnAssign) and isinstance(hijo.target, ast.Name):
                atributos.append(
                    (hijo.target.id, self._unparse(hijo.annotation) or "sin anotacion", None)
                )
            elif isinstance(hijo, ast.Assign):
                for objetivo in hijo.targets:
                    if isinstance(objetivo, ast.Attribute) and isinstance(objetivo.value, ast.Name):
                        if objetivo.value.id == "self":
                            atributos.append((objetivo.attr, "inferencia en el cuerpo", hijo.lineno))
        return atributos

    def _clase(self, nodo: ast.ClassDef) -> List[Tarjeta]:
        ubicacion = self._ubicar(nodo)
        completo = self._fragmento(nodo.lineno, getattr(nodo, "end_lineno", None), MAX_LINEAS_COMPLETO)
        fragmento = self._fragmento(nodo.lineno, getattr(nodo, "end_lineno", None), MAX_LINEAS_FRAGMENTO)
        bases = [self._unparse(base) for base in nodo.bases]
        metodos = [h for h in nodo.body if isinstance(h, (ast.FunctionDef, ast.AsyncFunctionDef))]
        init = next((m for m in metodos if m.name == "__init__"), None)
        publicos = [m.name for m in metodos if not m.name.startswith("_")]
        atributos = self._atributos(nodo)
        resultado: List[Tarjeta] = []
        if init is not None or atributos:
            firma_init = self._firma(init) if init is not None else "sin __init__ explicito"
            lista_atributos = ", ".join(f"`{nombre}`" for nombre, _, _ in atributos) or "ninguno"
            resultado.append(
                self.guia.construir_tarjeta(
                    "clase_constructor",
                    concepto=nodo.name,
                    respuesta=f"Firma: `{firma_init}`. Atributos inicializados: {lista_atributos}.",
                    explicacion=[
                        f"Inicializador: {firma_init}" if init is not None else "La clase no define `__init__`.",
                        f"Atributos de instancia ({len(atributos)}): "
                        + (", ".join(f"`{n}`: {t}" for n, t, _ in atributos[:MAX_LONGITUD_LISTADO]) or "ninguno"),
                        f"Hereda de: {', '.join(bases)}" if bases else "Sin herencia explicita.",
                        f"Ubicacion: {ubicacion}",
                    ],
                    codigo=fragmento,
                    codigo_completo=completo,
                    ubicacion=ubicacion,
                    archivo=self.etiqueta,
                    lenguaje="python",
                    complejidad=1 + len(atributos),
                    contexto_extra={"detalle": lista_atributos},
                )
            )

        if atributos:
            resultado.append(
                self.guia.construir_tarjeta(
                    "clase_atributos",
                    concepto=nodo.name,
                    respuesta="; ".join(f"`{n}`: {t}" for n, t, _ in atributos[:MAX_LONGITUD_LISTADO]),
                    explicacion=[
                        f"Total de atributos de instancia: {len(atributos)}.",
                        f"Metodos que pueden mutarlos: {len(publicos) or 'ninguno publico'}.",
                        f"Ubicacion: {ubicacion}",
                    ],
                    codigo=fragmento,
                    codigo_completo=completo,
                    ubicacion=ubicacion,
                    archivo=self.etiqueta,
                    lenguaje="python",
                    complejidad=1 + len(atributos),
                    contexto_extra={"detalle": ", ".join(n for n, _, _ in atributos[:3])},
                )
            )

        if publicos:
            resultado.append(
                self.guia.construir_tarjeta(
                    "clase_metodos",
                    concepto=nodo.name,
                    respuesta=", ".join(f"`{m}`" for m in publicos[:MAX_LONGITUD_LISTADO]),
                    explicacion=[
                        f"Metodos publicos: {len(publicos)} -> {', '.join(publicos[:MAX_LONGITUD_LISTADO])}.",
                        f"Metodos privados/especiales: {len(metodos) - len(publicos)}.",
                        f"Ubicacion: {ubicacion}",
                    ],
                    codigo=fragmento,
                    codigo_completo=completo,
                    ubicacion=ubicacion,
                    archivo=self.etiqueta,
                    lenguaje="python",
                    complejidad=len(publicos),
                    contexto_extra={"detalle": ", ".join(publicos[:3])},
                )
            )

        for metodo in metodos:
            nombre = metodo.name
            es_especial = nombre.startswith("__") and nombre.endswith("__")
            if es_especial or nombre == "__init__":
                continue
            resultado.extend(self._funcion(metodo, clase=nodo.name))
        return resultado

    def _constante(self, nodo: ast.AST) -> List[Tarjeta]:
        objetivos: List[str] = []
        valor = None
        if isinstance(nodo, ast.Assign):
            valor = nodo.value
            for objetivo in nodo.targets:
                if isinstance(objetivo, ast.Name):
                    objetivos.append(objetivo.id)
        elif isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name):
            objetivos.append(nodo.target.id)
            valor = nodo.value
        if valor is None:
            return []
        constantes = [
            nombre
            for nombre in objetivos
            if nombre.isupper() and any(caracter.isalpha() for caracter in nombre)
        ]
        if not constantes:
            return []
        texto_valor = self._unparse(valor)
        if len(texto_valor) > 140:
            texto_valor = recortar(texto_valor, 140)
        ubicacion = self._ubicar(nodo)
        fragmento = self._fragmento(nodo.lineno, getattr(nodo, "end_lineno", None), 4)
        resultado: List[Tarjeta] = []
        for nombre in constantes:
            resultado.append(
                self.guia.construir_tarjeta(
                    "constante_modulo",
                    concepto=nombre,
                    respuesta=f"{nombre} = {texto_valor}",
                    explicacion=[
                        f"Constante de modulo (NOMBRE_EN_MAYUSCULAS).",
                        f"Valor: `{texto_valor}`",
                        f"Ubicacion: {ubicacion}",
                    ],
                    codigo=fragmento,
                    ubicacion=ubicacion,
                    archivo=self.etiqueta,
                    lenguaje="python",
                    complejidad=1,
                )
            )
        return resultado

    def _imports(self, nodo: ast.AST) -> List[str]:
        nombres: List[str] = []
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                nombres.append(alias.name.split(".")[0])
        elif isinstance(nodo, ast.ImportFrom):
            base = nodo.module or ""
            nombres.append(base.split(".")[0] if base else f"relativo {'.' * (nodo.level or 0)}")
        return [nombre for nombre in nombres if nombre and nombre not in nombres]

    def _tarjeta_imports(self, imports: Sequence[str]) -> Tarjeta:
        estandar = getattr(sys, "stdlib_module_names", frozenset())
        propios = [nombre for nombre in imports if nombre in estandar]
        externos = [nombre for nombre in imports if nombre not in estandar]
        descripcion = ", ".join(f"`{nombre}`" for nombre in imports[:MAX_LONGITUD_LISTADO])
        lineas = [
            f"Importa {len(imports)} modulo(s): {descripcion}.",
            f"De la libreria estandar: {', '.join(propios) if propios else 'ninguno'}.",
            f"De terceros (deben estar en requirements.txt): {', '.join(externos) if externos else 'ninguno'}.",
        ]
        if not estandar:
            lineas.append("No se pudo clasificar estandar/terceros: requiere Python 3.10+ para la comparacion automatica.")
        return self.guia.construir_tarjeta(
            "dependencia_import",
            concepto=", ".join(imports[:3]) or "el modulo",
            respuesta=descripcion,
            explicacion=lineas,
            codigo="\n".join(f"import {nombre}" for nombre in imports[:MAX_LINEAS_FRAGMENTO]),
            ubicacion=self.etiqueta,
            archivo=self.etiqueta,
            lenguaje="python",
            complejidad=len(imports),
            contexto_extra={"detalle": descripcion},
        )

    def _flujo_modulo(self, nodo: ast.AST) -> Tarjeta:
        ubicacion = self._ubicar(nodo)
        representacion = self._unparse(nodo)
        primera_linea = representacion.splitlines()[0] if representacion else type(nodo).__name__
        descripcion = recortar(primera_linea, 120)
        return self.guia.construir_tarjeta(
            "flujo_control",
            concepto="el modulo",
            respuesta=f"Bloque `{type(nodo).__name__}` a nivel de modulo: {recortar(descripcion, 120)}",
            explicacion=[
                f"Tipo de bloque: `{type(nodo).__name__}`.",
                f"Condicion o recorrido: {recortar(descripcion, 160)}",
                f"Ubicacion: {ubicacion}",
            ],
            codigo=self._fragmento(nodo.lineno, getattr(nodo, "end_lineno", None), MAX_LINEAS_FRAGMENTO),
            codigo_completo=self._fragmento(nodo.lineno, getattr(nodo, "end_lineno", None), MAX_LINEAS_COMPLETO),
            ubicacion=ubicacion,
            archivo=self.etiqueta,
            lenguaje="python",
            complejidad=2,
            contexto_extra={"tipo": "modulo", "detalle": recortar(descripcion, 120)},
        )


# --------------------------------------------------------------------------
# Otros lenguajes (heuristico)
# --------------------------------------------------------------------------
class AnalizadorBloques:
    """Extractor heuristico para lenguajes sin AST disponible en la stdlib.

    Detecta funciones, clases y constantes por forma de la linea. No evalua el
    codigo: la guia de la tarjeta lo declara como heuristico para que el
    estudiante verifique contra el archivo original.
    """

    MODIFICADORES = (
        r"(?:export\s+)?(?:default\s+)?(?:declare\s+)?"
        r"(?:public\s+|private\s+|protected\s+|internal\s+|override\s+|readonly\s+|"
        r"abstract\s+|static\s+|async\s+|get\s+|set\s+)*"
    )
    NO_FUNCION = r"(?:if|for|while|switch|catch|return|do|else|try|elif|throw|await|yield|new|typeof|void|delete|case|import|from)"
    # Un nivel de anidamiento de parentesis: cubre valores por defecto como new Dto().
    # Debe ser el grupo 1 de los patrones de metodo: _funcion() lo recibe como argumentos.
    ARGUMENTOS = r"((?:[^()]|\([^()]*\))*)"
    SIN_PUNTO = r"(?![A-Za-z_$][\w$]*\s*\.\s*[A-Za-z_$])"

    PATRONES = (
        ("funcion", re.compile(r"^\s*(?:export\s+)?(?:public\s+|private\s+|static\s+|final\s+|async\s+)*function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)")),
        ("funcion", re.compile(r"^\s*(?:export\s+)?(?:public\s+|private\s+|protected\s+|static\s+|final\s+|async\s+)*(?:fun|func|def|sub)\s+([A-Za-z_][\w]*)\s*\(([^)]*)\)")),
        (
            "funcion",
            re.compile(
                r"^\s*(?:export\s+)?(?:default\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)"
                r"\s*(?::\s*[^=]+?)?=\s*(?:async\s+)?(?:<[^>]*>\s*)?\(([^;]*?)\)"
                r"\s*(?::\s*[^=]+?)?=>"
            ),
        ),
        ("funcion", re.compile(r"^\s*(?:pub\s+)?fn\s+([A-Za-z_][\w]*)\s*(?:<[^>]*>)?\s*\(([^)]*)\)")),
        # Metodo o funcion con cuerpo: admite modificadores y tipo de retorno de TypeScript.
        (
            "funcion",
            re.compile(
                r"^\s*" + MODIFICADORES + r"(?!" + NO_FUNCION + r"\b)" + SIN_PUNTO +
                r"([A-Za-z_$][\w$]*)\s*\(" + ARGUMENTOS + r"\)\s*(?::\s*[^;{]+?)?\s*\{\s*\}?\s*$"
            ),
        ),
        # Firma sin cuerpo (interfaces y clases abstractas): exige tipo de retorno.
        (
            "funcion",
            re.compile(
                r"^\s*" + MODIFICADORES + r"(?!" + NO_FUNCION + r"\b)" + SIN_PUNTO +
                r"([A-Za-z_$][\w$]*)\s*\(" + ARGUMENTOS + r"\)\s*:\s*[^;{]+;\s*$"
            ),
        ),
        ("clase", re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:public\s+|private\s+|abstract\s+|static\s+|final\s+|declare\s+)*(?:class|interface|struct|type|enum|record)\s+([A-Za-z_$][\w$]*)")),
        ("constante", re.compile(r"^\s*(?:export\s+)?(?:const|val|final|#define|let)\s+([A-Z][A-Z0-9_]{2,})\s*[:=]\s*(.+?);?\s*$")),
        # Constante de clase: static readonly LIMITE = 10;
        (
            "constante",
            re.compile(
                r"^\s*(?:(?:public\s+|private\s+|protected\s+|readonly\s+|declare\s+|static\s+|abstract\s+)+)"
                r"([A-Z][A-Z0-9_]{2,})\s*(?::\s*[^=;]+?)?=\s*(.+?);?\s*$"
            ),
        ),
    )

    def __init__(self, texto: str, etiqueta: str, guia: Guia, nombre: str, lenguaje: str) -> None:
        self.lineas = texto.splitlines()
        self.etiqueta = etiqueta
        self.guia = guia
        self.nombre = nombre
        self.lenguaje = lenguaje
        self.avisos: List[str] = []

    def _abre_firma(self, linea: str) -> bool:
        """True si la linea abre una declaracion con parentesis todavia sin cerrar."""
        if not re.match(
            r"^\s*" + self.MODIFICADORES + r"(?!" + self.NO_FUNCION + r"\b)" + self.SIN_PUNTO +
            r"[A-Za-z_$][\w$]*\s*\(",
            linea,
        ):
            return False
        return linea.count("(") > linea.count(")")

    def _unidades(self) -> List[Tuple[str, int]]:
        """Lineas del archivo, uniendo las firmas partidas en varias lineas.

        En TypeScript es habitual escribir la firma en varias lineas cuando hay
        parametros tipados como objeto:

            private toResponse(
              part: { id: string },
              role: string,
            ): SparePartResponseDto {

        Sin unirlas, cada parte se tomaria por separado y no se detectaria nada.
        """
        unidades: List[Tuple[str, int]] = []
        indice = 0
        total = len(self.lineas)
        while indice < total:
            numero = indice + 1
            linea = self.lineas[indice]
            if self._abre_firma(linea):
                unido = linea.strip()
                cursor = indice
                while (
                    cursor + 1 < total
                    and unido.count("(") > unido.count(")")
                    and cursor - indice < 40
                ):
                    cursor += 1
                    unido = unido + " " + self.lineas[cursor].strip()
                unidades.append((unido, numero))
                indice = cursor + 1
                continue
            unidades.append((linea, numero))
            indice += 1
        return unidades

    def tarjetas(self) -> List[Tarjeta]:
        resultado: List[Tarjeta] = []
        control = {"if": 0, "for": 0, "while": 0, "switch": 0, "try": 0}
        for linea, numero in self._unidades():
            limpio = linea.strip()
            if not limpio or limpio.startswith(("//", "#", "*", "/*")):
                continue
            for palabra in control:
                if re.match(rf"^\}}?\s*{palabra}\b", limpio) or limpio.startswith(palabra + " ") or limpio.startswith(palabra + "("):
                    control[palabra] += 1
                    break
            for tipo, patron in self.PATRONES:
                encontrado = patron.match(linea)
                if not encontrado:
                    continue
                grupos = encontrado.groups()
                if tipo == "clase":
                    resultado.append(self._clase(grupos[0], numero, linea))
                elif tipo == "constante":
                    resultado.append(self._constante(grupos[0], grupos[1], numero, linea))
                else:
                    resultado.append(self._funcion(grupos[0], grupos[1], numero, linea))
                break
        total_control = sum(control.values())
        if total_control:
            resultado.append(
                self.guia.construir_tarjeta(
                    "flujo_control",
                    concepto="el archivo",
                    respuesta="; ".join(f"{clave}: {valor}" for clave, valor in control.items() if valor),
                    explicacion=[
                        "Conteo heuristico de estructuras de control en el archivo.",
                        *[f"{clave}: {valor} ocurrencia(s)." for clave, valor in control.items() if valor],
                        f"Total: {total_control}.",
                        f"Analisis heuristico (sin AST para {NOMBRE_LENGUAJE.get(self.lenguaje, self.lenguaje)}): confirma en el archivo.",
                    ],
                    codigo="\n".join(
                        f"{numero}: {self.lineas[numero - 1]}"
                        for numero in range(1, len(self.lineas) + 1)
                        if re.search(r"\b(if|for|while|switch|try)\b", self.lineas[numero - 1])
                    )[:1200],
                    ubicacion=f"{self.etiqueta}:1",
                    archivo=self.etiqueta,
                    lenguaje=self.lenguaje,
                    complejidad=total_control,
                    tags_extra=["heuristico"],
                )
            )
        if resultado:
            self.avisos.append(
                f"analisis heuristico: no hay AST estandar para {NOMBRE_LENGUAJE.get(self.lenguaje, self.lenguaje)} en la libreria estandar."
            )
        return resultado

    def _fragmento(self, numero: int) -> str:
        return "\n".join(self.lineas[numero - 1 : numero + MAX_LINEAS_FRAGMENTO - 1])

    def _funcion(self, nombre: str, argumentos: str, numero: int, linea: str) -> Tarjeta:
        firma = f"{nombre}({' '.join(argumentos.split())})".replace("( ", "(").replace(" )", ")")
        lista = [p.strip() for p in argumentos.split(",") if p.strip()]
        ubicacion = f"{self.etiqueta}:{numero}"
        return self.guia.construir_tarjeta(
            "funcion_proposito",
            concepto=nombre,
            respuesta=(
                f"Firma detectada: `{firma}`.\n"
                f"El parser heuristico no sabe que hace: deducelo del cuerpo y del nombre."
            ),
            explicacion=[
                f"Parametros detectados: {len(lista)} -> {', '.join(lista) if lista else 'ninguno'}.",
                f"Cuerpo: empieza en la linea {numero} y sigue hasta la llave de cierre o el sangrado.",
                f"Analisis heuristico de linea: verifica la firma en `{self.etiqueta}:{numero}`.",
                f"Ubicacion: {ubicacion}",
            ],
            codigo=self._fragmento(numero),
            ubicacion=ubicacion,
            archivo=self.etiqueta,
            lenguaje=self.lenguaje,
            complejidad=len(lista) + 1,
            tags_extra=["heuristico"],
        )

    def _clase(self, nombre: str, numero: int, linea: str) -> Tarjeta:
        ubicacion = f"{self.etiqueta}:{numero}"
        return self.guia.construir_tarjeta(
            "clase_atributos",
            concepto=nombre,
            respuesta=f"Tipo declarado: `{nombre}`. Atributos y metodos: revisar el cuerpo.",
            explicacion=[
                f"Declaracion detectada: `{linea.strip()}`.",
                "Analisis heuristico: no se extraen atributos ni metodos de este lenguaje.",
                f"Ubicacion: {ubicacion}",
            ],
            codigo=self._fragmento(numero),
            ubicacion=ubicacion,
            archivo=self.etiqueta,
            lenguaje=self.lenguaje,
            complejidad=2,
            tags_extra=["heuristico"],
        )

    def _constante(self, nombre: str, valor: str, numero: int, linea: str) -> Tarjeta:
        ubicacion = f"{self.etiqueta}:{numero}"
        return self.guia.construir_tarjeta(
            "constante_modulo",
            concepto=nombre,
            respuesta=f"{nombre} = {recortar(valor, 80)}",
            explicacion=[
                f"Constante en mayusculas: {nombre}.",
                f"Valor: `{recortar(valor, 80)}`",
                f"Ubicacion: {ubicacion}",
            ],
            codigo=linea.strip(),
            ubicacion=ubicacion,
            archivo=self.etiqueta,
            lenguaje=self.lenguaje,
            complejidad=1,
            tags_extra=["heuristico"],
        )


# --------------------------------------------------------------------------
# Apuntes (.md / .txt)
# --------------------------------------------------------------------------
class AnalizadorNotas:
    """Extractor de tarjetas desde apuntes en Markdown o texto plano.

    Cuatro fuentes de tarjetas: secciones (`#`), terminos en negrita, listas de
    al menos dos elementos y bloques de codigo (que se delegan al analizador del
    lenguaje correspondiente).
    """

    CABECERA = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
    NEGRITA = re.compile(r"\*\*([^*\n]{2,60})\*\*")
    LISTA = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.+?)\s*$")

    def __init__(self, texto: str, etiqueta: str, guia: Guia, nombre: str) -> None:
        self.lineas = texto.splitlines()
        self.etiqueta = etiqueta
        self.guia = guia
        self.nombre = nombre
        self.avisos: List[str] = []
        self._descartar_frontmatter()

    def _descartar_frontmatter(self) -> None:
        if self.lineas and self.lineas[0].strip() == "---":
            for indice in range(1, len(self.lineas)):
                if self.lineas[indice].strip() == "---":
                    self.lineas = self.lineas[indice + 1 :]
                    return

    def tarjetas(self) -> List[Tarjeta]:
        resultado: List[Tarjeta] = []
        seccion = ""
        lista_actual: List[str] = []
        lista_linea = 0
        terminos: List[str] = []
        en_codigo = False
        lenguaje_bloque = ""
        buffer: List[str] = []
        inicio_bloque = 0
        seccion_bloque = ""

        def cerrar_lista() -> None:
            nonlocal lista_actual, lista_linea
            if len(lista_actual) >= 2:
                resultado.append(self._tarjeta_lista(seccion, lista_actual, lista_linea))
            lista_actual = []
            lista_linea = 0

        def cerrar_bloque() -> None:
            nonlocal buffer
            if buffer:
                resultado.extend(self._tarjetas_bloque(lenguaje_bloque, buffer, inicio_bloque, seccion_bloque))
            buffer = []

        for numero, linea in enumerate(self.lineas, start=1):
            if CERCA_FENCE.match(linea.strip()):
                if not en_codigo:
                    en_codigo = True
                    lenguaje_bloque = ALIAS_CERCA_FENCE.get(linea.strip().strip("`").lower(), "text")
                    buffer = []
                    inicio_bloque = numero
                    seccion_bloque = seccion or "el archivo"
                    cerrar_lista()
                else:
                    en_codigo = False
                    cerrar_bloque()
                continue
            if en_codigo:
                buffer.append(linea)
                continue
            if not linea.strip():
                cerrar_lista()
                continue
            cabecera = self.CABECERA.match(linea)
            if cabecera:
                cerrar_lista()
                nivel = len(cabecera.group(1))
                titulo = cabecera.group(2).strip()
                if titulo and nivel <= 4:
                    resultado.append(self._tarjeta_seccion(titulo, numero, nivel))
                    seccion = titulo
                continue
            item = self.LISTA.match(linea)
            if item:
                if not lista_actual:
                    lista_linea = numero
                lista_actual.append(item.group(1).strip())
                for termino in self.NEGRITA.findall(linea):
                    if not pertenece_a(termino, "diferencia") and termino not in terminos:
                        terminos.append(termino)
                continue
            cerrar_lista()
            for termino in self.NEGRITA.findall(linea):
                if not pertenece_a(termino, "diferencia") and termino not in terminos:
                    terminos.append(termino)
        cerrar_lista()
        cerrar_bloque()

        for termino in terminos[:MAX_TERMINOS_POR_ARCHIVO]:
            resultado.append(self._tarjeta_termino(termino, seccion))
        if not resultado:
            self.avisos.append(
                "sin secciones, listas, negritas ni bloques de codigo reconocibles."
            )
        return resultado

    def _primeras_lineas(self, inicio: int, limite: int) -> str:
        return "\n".join(self.lineas[inicio - 1 : inicio - 1 + limite])

    def _tarjeta_seccion(self, titulo: str, numero: int, nivel: int) -> Tarjeta:
        cuerpo: List[str] = []
        for linea in self.lineas[numero : numero + 8]:
            if not linea.strip():
                continue
            if self.CABECERA.match(linea) or self.LISTA.match(linea):
                break
            cuerpo.append(linea.strip())
        resumen = " ".join(cuerpo)[:400]
        elementos = [linea for linea in cuerpo if linea]
        return self.guia.construir_tarjeta(
            "nota_seccion",
            concepto=titulo,
            respuesta=(resumen or f"Seccion de nivel {nivel} en '{self.nombre}'."),
            explicacion=[
                f"Titulo de nivel {nivel} (h{'#' * nivel}).",
                f"Primeras ideas: {recortar(resumen, 240)}" if resumen else "La seccion no tiene parrafos, solo elementos de lista.",
                f"Ubicacion: {self.etiqueta}:{numero}",
            ],
            codigo=self._primeras_lineas(numero, 6),
            ubicacion=f"{self.etiqueta}:{numero}",
            archivo=self.etiqueta,
            lenguaje="text",
            complejidad=len(elementos),
        )

    def _tarjeta_termino(self, termino: str, seccion: str) -> Tarjeta:
        indice = self._linea_del_termino(termino)
        ubicacion = f"{self.etiqueta}:{indice}"
        return self.guia.construir_tarjeta(
            "nota_termino",
            concepto=termino,
            respuesta=f"Termino en negrita en la seccion '{seccion or self.nombre}'. Redefinelo con tus palabras.",
            explicacion=[
                f"Termino marcado en negrita: {termino}.",
                f"Seccion donde aparece: {seccion or 'sin seccion'}.",
                f"Ubicacion: {ubicacion}",
            ],
            codigo=self._primeras_lineas(indice, 3),
            ubicacion=ubicacion,
            archivo=self.etiqueta,
            lenguaje="text",
            complejidad=1,
        )

    def _linea_del_termino(self, termino: str) -> int:
        for numero, linea in enumerate(self.lineas, start=1):
            if f"**{termino}**" in linea:
                return numero
        return 1

    def _tarjeta_lista(self, seccion: str, elementos: Sequence[str], numero: int) -> Tarjeta:
        ubicacion = f"{self.etiqueta}:{numero}"
        titulo = seccion or f"lista de {self.nombre}"
        resumen = "; ".join(elementos[:MAX_LONGITUD_LISTADO])
        return self.guia.construir_tarjeta(
            "nota_lista",
            concepto=titulo,
            respuesta=recortar(resumen, 300),
            explicacion=[
                f"La lista tiene {len(elementos)} elementos (solo se generan tarjetas con 2 o mas).",
                *[f"{indice}. {recortar(elemento, 90)}" for indice, elemento in enumerate(elementos[:MAX_LONGITUD_LISTADO], start=1)],
                f"Ubicacion: {ubicacion}",
            ],
            codigo="\n".join(f"- {elemento}" for elemento in elementos[:MAX_LONGITUD_LISTADO]),
            ubicacion=ubicacion,
            archivo=self.etiqueta,
            lenguaje="text",
            complejidad=len(elementos),
        )

    def _tarjetas_bloque(self, lenguaje: str, buffer: Sequence[str], numero: int, seccion: str) -> List[Tarjeta]:
        texto = "\n".join(buffer)
        ubicacion = f"{self.etiqueta}:{numero}"
        resultado: List[Tarjeta] = [
            self.guia.construir_tarjeta(
                "codigo_en_notas",
                concepto=seccion,
                respuesta=(
                    f"Bloque de {lenguaje} con {len([l for l in buffer if l.strip()])} lineas "
                    f"en la seccion '{seccion}'."
                ),
                explicacion=[
                    f"Lenguaje del bloque: {lenguaje}.",
                    f"Lineas: {numero} a {numero + len(buffer)}.",
                    f"Ubicacion: {ubicacion}",
                ],
                codigo="\n".join(buffer[:MAX_LINEAS_FRAGMENTO]),
                codigo_completo="\n".join(buffer[:MAX_LINEAS_COMPLETO]),
                ubicacion=ubicacion,
                archivo=self.etiqueta,
                lenguaje=NOMBRE_LENGUAJE.get(lenguaje, "text"),
                complejidad=len([linea for linea in buffer if linea.strip()]),
                tags_extra=["notas"],
            )
        ]
        if lenguaje == "py":
            try:
                analizador = AnalizadorPython(texto, self.etiqueta, self.guia, self.nombre)
                derivadas = analizador.tarjetas()[:LIMITE_TARJETAS_POR_BLOQUE]
            except CodeParseError:
                derivadas = []
            resultado.extend(derivadas)
        elif len(texto.splitlines()) >= 2 and not pertenece_a(texto, "..."):
            analizador = AnalizadorBloques(
                texto, self.etiqueta, self.guia, self.nombre, lenguaje
            )
            resultado.extend(analizador.tarjetas()[:LIMITE_TARJETAS_POR_BLOQUE])
        if len(resultado) > 1:
            self.avisos.append(
                f"linea {numero}: {len(resultado)} tarjetas derivadas del bloque de codigo."
            )
        return resultado
