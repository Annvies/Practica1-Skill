"""Code Study & Flashcards Generator - nucleo compartido.

Este modulo concentra las piezas que no dependen del lenguaje de entrada:

- La jerarquia de errores `SkillError` (un unico lugar donde decidir el mensaje
  en espanol, la pista de correccion y el codigo de salida).
- La carga y validacion de `assets/flashcard_template.md` y
  `references/active_recall_guide.md`: si esos archivos no estan bien, el script
  aborta en vez de inventar contenido.
- Utilidades de normalizacion de texto y seleccion del patron de pregunta.

Las rutas por defecto se resuelven respecto a `__file__`, no al directorio de
trabajo: la skill se puede ejecutar desde cualquier carpeta.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

VERSION = "1.0.0"
RAIZ_SKILL = Path(__file__).resolve().parent.parent
PLANTILLA_POR_DEFECTO = RAIZ_SKILL / "assets" / "flashcard_template.md"
GUIA_POR_DEFECTO = RAIZ_SKILL / "references" / "active_recall_guide.md"

SALIDA_OK = 0
SALIDA_INESPERADA = 1
SALIDA_USO = 2
SALIDA_ENTRADA = 3
SALIDA_ASSETS = 4

DIFICULTADES = ("facil", "media", "dificil")
ORDEN_DIFICULTAD = {"facil": 0, "media": 1, "dificil": 2}

TOKENS_OBLIGATORIOS = (
    "{{TITULO}}",
    "{{ORIGEN}}",
    "{{TOTAL}}",
    "{{NUMERO}}",
    "{{CONCEPTO}}",
    "{{TIPO}}",
    "{{DIFICULTAD}}",
    "{{TAGS}}",
    "{{UBICACION}}",
    "{{PREGUNTA}}",
    "{{RESPUESTA}}",
    "{{EXPLICACION}}",
    "{{CODIGO}}",
)

MARCADOR_INICIO_REGLAS = "<!-- active-recall-rules:start -->"
MARCADOR_FIN_REGLAS = "<!-- active-recall-rules:end -->"
CERCA_JSON = re.compile(r"```json\s*(.*?)```", re.DOTALL)
MARCADOR_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


# --------------------------------------------------------------------------
# Errores
# --------------------------------------------------------------------------
class SkillError(Exception):
    """Error controlado de la skill: mensaje claro, pista y codigo de salida."""

    exit_code = SALIDA_INESPERADA
    etiqueta = "ERROR"

    def __init__(self, mensaje: str, pista: Optional[str] = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.pista = pista

    def render(self) -> str:
        lineas = [f"[{self.etiqueta}] {self.mensaje}"]
        if self.pista:
            lineas.append(f"  Sugerencia: {self.pista}")
        return "\n".join(lineas)


class UsageError(SkillError):
    """Los argumentos que recibio el programa no son validos."""

    exit_code = SALIDA_USO
    etiqueta = "ERROR: uso incorrecto"


class InputNotFoundError(SkillError):
    """La ruta de entrada no existe."""

    exit_code = SALIDA_ENTRADA
    etiqueta = "ERROR: entrada no encontrada"


class LecturaError(SkillError):
    """La entrada existe pero el sistema operativo no deja leerla."""

    exit_code = SALIDA_ENTRADA
    etiqueta = "ERROR: no se pudo leer la entrada"


class EmptyInputError(SkillError):
    """El archivo esta vacio o solo contiene espacios."""

    exit_code = SALIDA_ENTRADA
    etiqueta = "ERROR: entrada vacia"


class UnsupportedFormatError(SkillError):
    """La extension no corresponde a ningun analizador."""

    exit_code = SALIDA_ENTRADA
    etiqueta = "ERROR: formato no soportado"


class DecodingError(SkillError):
    """El archivo es binario o no se puede decodificar a texto."""

    exit_code = SALIDA_ENTRADA
    etiqueta = "ERROR: archivo ilegible"


class CodeParseError(SkillError):
    """El archivo tiene extension de codigo pero no se puede parsear."""

    exit_code = SALIDA_ENTRADA
    etiqueta = "ERROR: codigo no parseable"


class NoCardsFoundError(SkillError):
    """Se leyo la entrada pero no hay nada que convertir en tarjetas."""

    exit_code = SALIDA_ENTRADA
    etiqueta = "ERROR: sin tarjetas generadas"


class TemplateError(SkillError):
    """`assets/flashcard_template.md` falta o no tiene los tokens requeridos."""

    exit_code = SALIDA_ASSETS
    etiqueta = "ERROR: plantilla invalida"


class GuideError(SkillError):
    """`references/active_recall_guide.md` falta o su configuracion es invalida."""

    exit_code = SALIDA_ASSETS
    etiqueta = "ERROR: guia de referencia invalida"


class OutputError(SkillError):
    """No se pudo escribir el archivo de salida."""

    exit_code = SALIDA_ENTRADA
    etiqueta = "ERROR: no se pudo escribir la salida"


# --------------------------------------------------------------------------
# Texto
# --------------------------------------------------------------------------
def normalizar(texto: str) -> str:
    """Minusculas sin acentos y con espacios colapsados, para comparar."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    sin_acentos = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sin_acentos).strip()


def pertenece_a(texto: str, frase: str) -> bool:
    """Busca `frase` dentro de `texto` ignorando mayusculas y acentos."""
    return normalizar(frase) in normalizar(texto)


def ajustar_dificultad(base: str, complejidad: int) -> str:
    """Sube un nivel de dificultad si el concepto es mas denso de lo normal."""
    if complejidad >= 4 and ORDEN_DIFICULTAD.get(base, 0) < ORDEN_DIFICULTAD["dificil"]:
        return "dificil"
    if complejidad == 3 and ORDEN_DIFICULTAD.get(base, 0) == 0:
        return "media"
    return base


def recortar(texto: str, limite: int = 220) -> str:
    """Recorta a un maximo de caracteres y agrega puntos suspensivos."""
    limpio = " ".join(str(texto).split())
    if len(limpio) <= limite:
        return limpio
    return limpio[: limite - 1].rstrip() + "…"


def vinietas(lineas: Sequence[str], sangria: str = "- ") -> str:
    """Une lineas como lista Markdown; devuelve cadena vacia si no hay lineas."""
    utiles = [l for l in (linea.strip() for linea in lineas) if l]
    if not utiles:
        return ""
    return "\n".join(f"{sangria}{l}" for l in utiles)


def lista_en_lineas(valor: Any) -> List[str]:
    """Normaliza cualquier valor a lista de strings legibles."""
    if valor is None:
        return []
    if isinstance(valor, str):
        return [valor] if valor.strip() else []
    if isinstance(valor, (list, tuple, set)):
        salida: List[str] = []
        for item in valor:
            salida.extend(lista_en_lineas(item))
        return salida
    return [str(valor)]


def sangrar_bloque(texto: str, sangria: str = "    ") -> str:
    """Indenta un bloque multilinea para mantenerlo legible dentro de Markdown."""
    return "\n".join(f"{sangria}{linea}" if linea.strip() else "" for linea in texto.splitlines())


def ruta_legible(ruta: Path) -> str:
    """Muestra la ruta relativa al directorio actual cuando se puede, en posix."""
    try:
        return ruta.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except (ValueError, OSError):
        return ruta.as_posix()


# --------------------------------------------------------------------------
# Guia de referencia
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Regla:
    """Regla pedagogica declarada en la guia (R1..Rn)."""

    id: str
    nombre: str
    descripcion: str = ""

    def citar(self) -> str:
        return f"{self.id} {self.nombre}"


@dataclass(frozen=True)
class TipoTarjeta:
    """Tipo de tarjeta (una familia de conocimiento) con sus reglas y patrones."""

    clave: str
    etiqueta: str
    icono: str
    dificultad: str
    tags: Tuple[str, ...]
    reglas: Tuple[str, ...]
    preguntas: Tuple[str, ...]

    def placeholders(self, indice: int) -> Tuple[str, ...]:
        return tuple(MARCADOR_PLACEHOLDER.findall(self.preguntas[indice]))


@dataclass
class Guia:
    """Contenido machine-readable de `references/active_recall_guide.md`."""

    version: str
    ruta: Path
    reglas: Dict[str, Regla] = field(default_factory=dict)
    tipos: Dict[str, TipoTarjeta] = field(default_factory=dict)
    separador_anki: str = "\t"

    def resumen_reglas(self) -> str:
        return ", ".join(sorted(self.reglas)) if self.reglas else "sin reglas"

    def regla_de(self, tipo: TipoTarjeta) -> Optional[Regla]:
        for identificador in tipo.reglas:
            if identificador in self.reglas:
                return self.reglas[identificador]
        return None

    def elegir_pregunta(self, clave_tipo: str, contexto: Mapping[str, Any]) -> Tuple[str, str]:
        """Devuelve (pregunta, id de regla) usando el primer patron disponible.

        Se descarta cualquier patron cuyo marcador no exista en el contexto, de
        modo que la pregunta impresa nunca lleva un `{{...}}` sin resolver.
        """
        tipo = self.tipos[clave_tipo]
        for indice in range(len(tipo.preguntas)):
            if set(tipo.placeholders(indice)) <= set(contexto):
                return aplicar_placeholders(tipo.preguntas[indice], contexto), tipo.reglas[0]
        patron = "Repasa {nombre} en {archivo}: explica que hace y por que importa."
        return aplicar_placeholders(patron, contexto), tipo.reglas[0]

    def construir_tarjeta(
        self,
        clave_tipo: str,
        concepto: str,
        respuesta: str,
        explicacion: Sequence[str],
        codigo: str,
        ubicacion: str,
        archivo: str,
        lenguaje: str,
        contexto_extra: Optional[Mapping[str, Any]] = None,
        complejidad: int = 0,
        tags_extra: Sequence[str] = (),
        codigo_completo: str = "",
    ) -> "Tarjeta":
        """Crea una `Tarjeta` ya normalizada, con pregunta y regla aplicadas."""
        tipo = self.tipos[clave_tipo]
        contexto: Dict[str, Any] = {"nombre": concepto, "archivo": archivo, "lenguaje": lenguaje}
        if contexto_extra:
            contexto.update(contexto_extra)
        pregunta, regla_id = self.elegir_pregunta(clave_tipo, contexto)
        regla = self.reglas.get(regla_id)
        etiquetas = []
        for t in list(tipo.tags) + [lenguaje] + list(tags_extra):
            if t and t not in etiquetas:
                etiquetas.append(t)
        if not any("dificil" == t or "facil" == t for t in etiquetas):
            etiquetas.append(ajustar_dificultad(tipo.dificultad, complejidad))
        return Tarjeta(
            tipo_clave=clave_tipo,
            tipo_etiqueta=tipo.etiqueta,
            icono=tipo.icono,
            concepto=concepto,
            pregunta=pregunta,
            respuesta=recortar(respuesta, 600),
            explicacion=vinietas(explicacion),
            codigo=codigo.strip("\n"),
            codigo_completo=(codigo_completo or codigo).strip("\n"),
            ubicacion=ubicacion,
            lenguaje=lenguaje,
            dificultad=etiquetas[-1] if etiquetas[-1] in DIFICULTADES else tipo.dificultad,
            tags=etiquetas,
            regla=regla.citar() if regla else "sin regla",
            reglas=tipo.reglas,
        )


@dataclass
class Tarjeta:
    """Una tarjeta de estudio ya resuelta, lista para renderizar."""

    tipo_clave: str
    tipo_etiqueta: str
    icono: str
    concepto: str
    pregunta: str
    respuesta: str
    explicacion: str
    codigo: str
    codigo_completo: str
    ubicacion: str
    lenguaje: str
    dificultad: str
    tags: List[str]
    regla: str
    reglas: Tuple[str, ...]

    @property
    def etiquetas(self) -> str:
        return ", ".join(self.tags)


def aplicar_placeholders(patron: str, contexto: Mapping[str, Any]) -> str:
    """Sustituye `{{clave}}` por el valor del contexto; deja intacto lo demas."""

    def _sustituir(match: "re.Match[str]") -> str:
        clave = match.group(1)
        if clave in contexto:
            return str(contexto[clave])
        return match.group(0)

    return MARCADOR_PLACEHOLDER.sub(_sustituir, patron)


# --------------------------------------------------------------------------
# Carga de assets y referencias
# --------------------------------------------------------------------------
def _leer_texto_legible(ruta: Path, clase_error, etiqueta: str) -> str:
    """Lee un archivo de la propia skill validando existencia y decodificacion."""
    if not ruta.exists():
        raise clase_error(
            f"No se encontro {etiqueta}: {ruta}",
            pista=(
                "Instala la skill completa (deben existir assets/ y references/). "
                "En un clon: revisa que no falte ningun archivo versionado."
            ),
        )
    try:
        datos = ruta.read_bytes()
    except OSError as exc:
        raise clase_error(
            f"No se pudo leer {etiqueta}: {ruta} ({exc.strerror or exc})",
            pista="Comprueba los permisos del archivo.",
        )
    for codificacion in ("utf-8", "cp1252", "latin-1"):
        try:
            texto = datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
        return texto[1:] if texto.startswith("\ufeff") else texto
    raise clase_error(
        f"{etiqueta} usa una codificacion no soportada: {ruta}",
        pista="Guardo la plantilla y la guia en UTF-8.",
    )


def cargar_guia(ruta: Path = GUIA_POR_DEFECTO) -> Guia:
    """Carga y valida el JSON pedagogico embebido en la guia de referencia."""
    texto = _leer_texto_legible(ruta, GuideError, "la guia de referencia")
    if MARCADOR_INICIO_REGLAS not in texto or MARCADOR_FIN_REGLAS not in texto:
        raise GuideError(
            f"La guia '{ruta.name}' no tiene el bloque de configuracion.",
            pista=(
                f"Debe incluir {MARCADOR_INICIO_REGLAS} ... {MARCADOR_FIN_REGLAS} "
                "con un bloque ```json``` dentro. Revisa references/active_recall_guide.md."
            ),
        )
    bloque = texto.rsplit(MARCADOR_INICIO_REGLAS, 1)[1].split(MARCADOR_FIN_REGLAS, 1)[0]
    encontrado = CERCA_JSON.search(bloque)
    if not encontrado:
        raise GuideError(
            f"El bloque de configuracion de '{ruta.name}' no contiene un bloque ```json```.",
            pista="El JSON va entre triple backtick y la palabra json.",
        )
    try:
        datos = json.loads(encontrado.group(1))
    except json.JSONDecodeError as exc:
        raise GuideError(
            f"El JSON de '{ruta.name}' es invalido (linea {exc.lineno}, columna {exc.colno}): {exc.msg}",
            pista="Corrige el JSON en references/active_recall_guide.md; no puede tener comas finales.",
        )
    if not isinstance(datos, dict):
        raise GuideError(f"El JSON de '{ruta.name}' debe ser un objeto.", pista="La raiz debe ser { ... }.")

    reglas: Dict[str, Regla] = {}
    for entrada in datos.get("reglas", []) or []:
        if not isinstance(entrada, dict) or "id" not in entrada:
            raise GuideError(
                f"Una regla de '{ruta.name}' no tiene 'id'.", pista="Cada regla necesita id, nombre y descripcion."
            )
        regla = Regla(
            id=str(entrada["id"]),
            nombre=str(entrada.get("nombre", entrada["id"])),
            descripcion=str(entrada.get("descripcion", "")),
        )
        reglas[regla.id] = regla

    tipos_raw = datos.get("tipos")
    if not isinstance(tipos_raw, dict) or not tipos_raw:
        raise GuideError(
            f"La guia '{ruta.name}' no define 'tipos'.",
            pista="El objeto 'tipos' debe listar al menos un tipo de tarjeta.",
        )
    tipos: Dict[str, TipoTarjeta] = {}
    for clave, bruto in tipos_raw.items():
        if not isinstance(bruto, dict):
            raise GuideError(f"El tipo '{clave}' no es un objeto.", pista="Cada tipo es { etiqueta, dificultad, tags, preguntas }.")
        faltantes = [campo for campo in ("etiqueta", "dificultad", "preguntas") if not bruto.get(campo)]
        if faltantes:
            raise GuideError(
                f"El tipo '{clave}' de la guia no tiene: {', '.join(faltantes)}.",
                pista="Cada tipo necesita etiqueta, dificultad y al menos un patron en preguntas.",
            )
        dificultad = str(bruto["dificultad"]).lower()
        if dificultad not in DIFICULTADES:
            raise GuideError(
                f"El tipo '{clave}' usa dificultad '{dificultad}', no permitida.",
                pista=f"Valores validos: {', '.join(DIFICULTADES)}.",
            )
        preguntas = tuple(str(p) for p in bruto["preguntas"])
        reglas_tipo = tuple(str(r) for r in bruto.get("reglas", []) or [])
        reglas_desconocidas = [r for r in reglas_tipo if r not in reglas]
        if reglas_desconocidas:
            raise GuideError(
                f"El tipo '{clave}' referencia reglas inexistentes: {', '.join(reglas_desconocidas)}.",
                pista=f"Reglas declaradas: {', '.join(sorted(reglas)) or 'ninguna'}.",
            )
        tipos[clave] = TipoTarjeta(
            clave=clave,
            etiqueta=str(bruto["etiqueta"]),
            icono=str(bruto.get("icono", clave)),
            dificultad=dificultad,
            tags=tuple(str(t) for t in bruto.get("tags", []) or []),
            reglas=reglas_tipo or tuple(sorted(reglas))[:1],
            preguntas=preguntas,
        )

    separador = str((datos.get("formato_anki") or {}).get("separador", "\t"))
    guia = Guia(
        version=str(datos.get("version", "sin version")),
        ruta=ruta,
        reglas=reglas,
        tipos=tipos,
        separador_anki=separador if len(separador) == 1 else "\t",
    )
    return guia


def cargar_plantilla(ruta: Path = PLANTILLA_POR_DEFECTO) -> str:
    """Carga la plantilla y verifica tokens, separadores y zona de tarjeta."""
    texto = _leer_texto_legible(ruta, TemplateError, "la plantilla")
    if not texto.strip():
        raise TemplateError(
            f"La plantilla '{ruta.name}' esta vacia.",
            pista="Restaura assets/flashcard_template.md o indica otra con --template.",
        )
    faltantes = [token for token in TOKENS_OBLIGATORIOS if token not in texto]
    if faltantes:
        raise TemplateError(
            f"La plantilla '{ruta.name}' no tiene estos tokens: {', '.join(faltantes)}.",
            pista="Restaura assets/flashcard_template.md o usa --template con una plantilla compatible.",
        )
    zonas = descomponer_plantilla(texto, f"la plantilla '{ruta.name}'")
    if not zonas.bloque_tarjeta.strip():
        raise TemplateError(
            f"La plantilla '{ruta.name}' tiene el bloque de tarjeta vacio.",
            pista="El bloque entre la primera y la segunda linea '---' es el que se repite por tarjeta.",
        )
    return texto


# --------------------------------------------------------------------------
# Renderizado
# --------------------------------------------------------------------------
def _sustituir_tokens(bloque: str, valores: Mapping[str, Any]) -> str:
    """Sustituye todos los tokens presentes; los desconocidos quedan intactos."""
    return MARCADOR_PLACEHOLDER.sub(lambda m: str(valores.get(m.group(1), m.group(0))), bloque)


@dataclass(frozen=True)
class Plantilla:
    """Plantilla descompuesta en las tres zonas que el renderizador rellena."""

    frontmatter: str
    cabecera: str
    bloque_tarjeta: str
    pie: str


def descomponer_plantilla(plantilla: str, nombre: str = "la plantilla") -> Plantilla:
    """Separa frontmatter, cabecera, bloque de tarjeta y pie de la plantilla.

    Estructura esperada (los `---` son lineas completas):

        [--- frontmatter ---]
        cabecera
        ---
        bloque de tarjeta
        ---
        pie (opcional)
    """
    lineas = plantilla.splitlines()
    cuerpo_inicio = 0
    frontmatter = ""
    if lineas and lineas[0].strip() == "---":
        for indice in range(1, len(lineas)):
            if lineas[indice].strip() == "---":
                frontmatter = "\n".join(lineas[: indice + 1])
                cuerpo_inicio = indice + 1
                break
    separadores = [
        indice for indice in range(cuerpo_inicio, len(lineas)) if lineas[indice].strip() == "---"
    ]
    if not separadores:
        raise TemplateError(
            f"{nombre} no tiene una linea '---' que separe la cabecera del bloque de tarjeta.",
            pista=(
                "Estructura esperada: cabecera, linea '---', bloque de tarjeta, linea '---', pie. "
                "Restaura assets/flashcard_template.md."
            ),
        )
    primero = separadores[0]
    segundo = separadores[1] if len(separadores) > 1 else len(lineas)
    return Plantilla(
        frontmatter=frontmatter,
        cabecera="\n".join(lineas[cuerpo_inicio:primero]).strip("\n"),
        bloque_tarjeta="\n".join(lineas[primero + 1 : segundo]).strip("\n"),
        pie="\n".join(lineas[segundo + 1 :]).strip("\n") if len(separadores) > 1 else "",
    )


def render_markdown(plantilla: str, tarjetas: Sequence[Tarjeta], meta: Mapping[str, Any]) -> str:
    """Rellena la plantilla con todas las tarjetas y devuelve el Markdown final.

    La cabecera (con su frontmatter) se imprime una vez, el bloque central se
    replica por cada tarjeta y el pie cierra el documento.
    """
    zonas = descomponer_plantilla(plantilla)
    contexto_global = dict(meta)
    contexto_global["TOTAL"] = len(tarjetas)

    cabecera = ""
    if zonas.frontmatter:
        cabecera += _sustituir_tokens(zonas.frontmatter, contexto_global) + "\n\n"
    cabecera += _sustituir_tokens(zonas.cabecera, contexto_global)

    cuerpos: List[str] = []
    for indice, tarjeta in enumerate(tarjetas, start=1):
        valores = dict(contexto_global)
        valores.update(
            {
                "NUMERO": str(indice),
                "CONCEPTO": tarjeta.concepto,
                "TIPO": tarjeta.tipo_etiqueta,
                "ICONO": tarjeta.icono,
                "DIFICULTAD": tarjeta.dificultad,
                "TAGS": tarjeta.etiquetas,
                "UBICACION": tarjeta.ubicacion,
                "PREGUNTA": tarjeta.pregunta,
                "RESPUESTA": tarjeta.respuesta,
                "EXPLICACION": tarjeta.explicacion,
                "CODIGO": tarjeta.codigo,
                "CODIGO_ORIGINAL": tarjeta.codigo_completo,
                "LENGUAJE": tarjeta.lenguaje,
                "REGLA": tarjeta.regla,
                "REGLAS": ", ".join(tarjeta.reglas),
                "TOTAL": str(len(tarjetas)),
            }
        )
        cuerpos.append(_sustituir_tokens(zonas.bloque_tarjeta, valores))

    piezas: List[str] = [cabecera.rstrip("\n")]
    if cuerpos:
        piezas.append("\n\n---\n\n".join(cuerpos).rstrip("\n"))
    if zonas.pie:
        piezas.append(zonas.pie.rstrip("\n"))
    return "\n\n---\n\n".join(pieza for pieza in piezas if pieza) + "\n"


def render_anki(tarjetas: Sequence[Tarjeta], guia: Guia) -> str:
    """Exporta en formato texto tab-separado, importable desde Anki.

    Cada registro es una sola linea: los saltos de linea internos se convierten
    en espacios para que el importador de Anki no los confunda con el comienzo
    de una fila nueva.
    """
    separador = guia.separador_anki

    def una_linea(texto: str) -> str:
        return " ".join(str(texto).split()).replace(separador, " ")

    lineas = [
        "#separator:Tab",
        "#html:false",
        "#columns:front" + separador + "back" + separador + "tags",
        "#tags column:3",
    ]
    for tarjeta in tarjetas:
        frente = una_linea(tarjeta.pregunta)
        reverso = una_linea(f"Respuesta: {tarjeta.respuesta} | Explicacion: {tarjeta.explicacion}")
        etiquetas = [t for t in tarjeta.tags if t]
        if tarjeta.reglas:
            etiquetas.append(f"regla_{tarjeta.reglas[0]}")
        lineas.append(separador.join([frente, reverso, ",".join(etiquetas)]))
    return "\n".join(lineas) + "\n"


def escribir_salida(ruta: Path, contenido: str) -> Path:
    """Escribe la salida creando el directorio destino si hace falta."""
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8", newline="\n")
    except OSError as exc:
        raise OutputError(
            f"No se pudo escribir la salida en '{ruta}': {exc.strerror or exc}",
            pista="Elige otra ruta con -o/--output o revisa los permisos de la carpeta.",
        )
    return ruta


def fecha_hoy() -> str:
    """Fecha ISO de hoy, para la cabecera de las tarjetas."""
    return date.today().isoformat()
