"""Pruebas de code-study-flashcards con la libreria estandar (unittest).

Ejecucion desde la raiz de la skill:

    python -m unittest discover -s tests -v

Cada prueba comprueba dos cosas: el codigo de salida del script y el contenido
del mensaje o del archivo generado. Los casos de error son parte del entregable:
documentan que ocurre con una entrada invalida.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ_SKILL = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ_SKILL / "scripts" / "generate_cards.py"
EJEMPLOS = RAIZ_SKILL / "examples"
CODIGO_VALIDO = EJEMPLOS / "input_sample.py"
APUNTES = EJEMPLOS / "notas_sample.md"


def ejecutar(*argumentos: str) -> subprocess.CompletedProcess:
    """Corre el script como proceso aparte, igual que lo haria un usuario."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argumentos],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(RAIZ_SKILL),
    )


class BasePrueba(unittest.TestCase):
    """Utilidades comunes: carpeta temporal y lectura de la salida."""

    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.carpeta = Path(self.temporal.name)
        self.salida = self.carpeta / "tarjetas.md"

    def tearDown(self) -> None:
        self.temporal.cleanup()

    def combo(self, *extra: str) -> list:
        return ["-i", str(CODIGO_VALIDO), "-o", str(self.salida), *extra]

    def texto_salida(self) -> str:
        return self.salida.read_text(encoding="utf-8")


class CasoExitoso(BasePrueba):
    """Caso feliz: el flujo completo produce tarjetas utilizables."""

    def test_genera_markdown_desde_codigo_python(self) -> None:
        resultado = ejecutar(*self.combo())
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertTrue(self.salida.exists())
        contenido = self.texto_salida()
        self.assertIn("total_tarjetas:", contenido)
        self.assertIn("### Pregunta", contenido)
        self.assertIn("### Respuesta", contenido)
        self.assertIn("### Explicación", contenido)
        self.assertIn("resumen_inventario", contenido)
        self.assertIn("Inventario", contenido)

    def test_no_deja_tokens_sin_resolver(self) -> None:
        resultado = ejecutar(*self.combo())
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        contenido = self.texto_salida()
        self.assertNotIn("{{", contenido, "quedaron tokens de la plantilla sin resolver")
        self.assertIn("## Tarjeta 1", contenido)

    def test_cubre_funciones_clases_y_constantes(self) -> None:
        ejecutar(*self.combo())
        contenido = self.texto_salida()
        for etiqueta in (
            "Proposito de funcion",
            "Parametros",
            "Valor de retorno",
            "Constructor e inicializacion",
            "Metodos publicos",
            "Constantes y configuracion",
            "Flujo de control",
        ):
            self.assertIn(etiqueta, contenido, f"falta el tipo de tarjeta '{etiqueta}'")

    def test_detecta_huecos_de_documentacion(self) -> None:
        ejecutar(*self.combo())
        contenido = self.texto_salida()
        self.assertIn("Hueco de documentacion", contenido)
        self.assertIn("gap", contenido)

    def test_procesa_apuntes_markdown(self) -> None:
        resultado = ejecutar("-i", str(APUNTES), "-o", str(self.salida))
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        contenido = self.texto_salida()
        self.assertIn("Seccion de apuntes", contenido)
        self.assertIn("Termino clave", contenido)
        self.assertIn("Lista de apuntes", contenido)

    def test_procesa_javascript_en_modo_heuristico(self) -> None:
        resultado = ejecutar("-i", str(EJEMPLOS / "input_sample.js"), "-o", str(self.salida))
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn("heuristico", resultado.stdout)
        self.assertIn("validarCampos", self.texto_salida())

    def test_detecta_metodos_y_constantes_de_un_servicio_typescript(self) -> None:
        """Firma TypeScript con tipo de retorno, modificadores y salto de linea.

        Es el caso que fallaba con el patron ingenuo: solo reconocia
        `nombre(args) {`, por lo que un servicio NestJS entero se quedaba sin
        tarjetas. Se comprueban las cinco variantes y que no se cuele ninguna
        llamada interna como si fuera una declaracion.
        """
        resultado = ejecutar("-i", str(EJEMPLOS / "input_sample.ts"), "-o", str(self.salida))
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn("heuristico", resultado.stdout)
        contenido = self.texto_salida()
        for concepto in (
            "RepuestosService",          # clase
            "DIAS_ROTACION_LENTA",       # constante static readonly
            "MAX_POR_PAGINA",            # constante static readonly
            "constructor",               # constructor con inyeccion de dependencias
            "findAll",                   # async con tipo de retorno generico
            "buscarPorCodigo",           # async con tipo de retorno
            "registrarAjuste",           # firma partida en varias lineas
            "resumir",                   # metodo private con parametro objeto
            "ordenarPorRotacion",        # function exportada
        ):
            self.assertIn(concepto, contenido, f"falta el concepto {concepto}")
        # Una llamada interna no es una declaracion: no debe generar tarjeta.
        # El fragmento de codigo si puede mostrarla, por eso se revisan los titulos.
        titulos = [linea for linea in contenido.splitlines() if linea.startswith("## Tarjeta")]
        self.assertTrue(titulos)
        for titulo in titulos:
            self.assertNotIn("repositorio", titulo, f"llamada interna tratada como metodo: {titulo}")
            self.assertNotIn("Math.min", titulo, f"expresion interna tratada como metodo: {titulo}")

    def test_max_cards_recorta_el_resultado(self) -> None:
        resultado = ejecutar(*self.combo("--max-cards", "5"))
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn("5 tarjetas generadas", resultado.stdout)
        self.assertNotIn("## Tarjeta 6", self.texto_salida())

    def test_recorre_una_carpeta_completa(self) -> None:
        resultado = ejecutar("-i", str(EJEMPLOS), "-r", "-o", str(self.salida), "--quiet")
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        contenido = self.texto_salida()
        self.assertIn("input_sample.py", contenido)
        self.assertIn("notas_sample.md", contenido)

    def test_ignora_codigo_generado_y_declaraciones_de_tipos(self) -> None:
        """Una carpeta con 'generated/' y '.d.ts' no debe generar tarjetas de ellas."""
        proyecto = self.carpeta / "proyecto"
        (proyecto / "src" / "generated").mkdir(parents=True)
        (proyecto / "src" / "types").mkdir(parents=True)
        (proyecto / "src" / "generated" / "modelo.ts").write_text(
            "export class Modelo {\n  campo: string;\n}\n", encoding="utf-8"
        )
        (proyecto / "src" / "types" / "api.d.ts").write_text(
            "export declare function obtener(): void;\n", encoding="utf-8"
        )
        servicio = proyecto / "src" / "servicio.ts"
        servicio.write_text(CODIGO_VALIDO.read_text(encoding="utf-8"), encoding="utf-8")

        resultado = ejecutar("-i", str(proyecto), "-r", "-o", str(self.salida), "--quiet")
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        contenido = self.texto_salida()
        self.assertIn("servicio.ts", contenido)
        self.assertNotIn("modelo.ts", contenido)
        self.assertNotIn("api.d.ts", contenido)

    def test_crea_el_directorio_de_salida_si_no_existe(self) -> None:
        destino = self.carpeta / "anidado" / "más" / "tarjetas.md"
        resultado = ejecutar("-i", str(CODIGO_VALIDO), "-o", str(destino), "--quiet")
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertTrue(destino.exists())


class ExportAnki(BasePrueba):
    """El formato Anki debe ser texto separado por tabuladores."""

    def test_exporta_tsv_con_encabezado_de_anki(self) -> None:
        destino = self.carpeta / "anki.txt"
        resultado = ejecutar("-i", str(CODIGO_VALIDO), "--format", "anki", "-o", str(destino))
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        lineas = destino.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lineas[0], "#separator:Tab")
        self.assertIn("#tags column:3", lineas)
        filas = [linea for linea in lineas if linea and not linea.startswith("#")]
        self.assertTrue(filas)
        for fila in filas:
            self.assertEqual(len(fila.split("\t")), 3, f"fila con numero de columnas raro: {fila[:60]}")

    def test_no_emite_header_columns_que_descarta_el_reverso(self) -> None:
        """Regresion: #columns no asigna campos, Anki tiraba la columna del reverso.

        Segun el manual de Anki, #columns solo cuenta las columnas y muestra sus
        nombres al importar. Con el, el importador mapeaba la columna 1 al
        Anverso y descartaba la 2, dejando 15 notas con el Reverso vacio y sin
        ningun aviso. El export no debe emitirlo.
        """
        destino = self.carpeta / "anki.txt"
        resultado = ejecutar("-i", str(CODIGO_VALIDO), "--format", "anki", "-o", str(destino))
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        lineas = destino.read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            [linea for linea in lineas if linea.startswith("#columns:")],
            [],
            "el export no debe emitir #columns: porque Anki no lo usa para asignar campos",
        )

    def test_todas_las_filas_tienen_anverso_y_reverso_rellenos(self) -> None:
        destino = self.carpeta / "anki.txt"
        resultado = ejecutar("-i", str(CODIGO_VALIDO), "--format", "anki", "-o", str(destino))
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        filas = [
            linea
            for linea in destino.read_text(encoding="utf-8").splitlines()
            if linea and not linea.startswith("#")
        ]
        self.assertTrue(filas)
        for fila in filas:
            frente, reverso, etiquetas = fila.split("\t")
            self.assertTrue(frente.strip(), f"anverso vacio: {fila[:60]}")
            self.assertTrue(reverso.strip(), f"reverso vacio: {fila[:60]}")
            self.assertTrue(etiquetas.strip(), f"etiquetas vacias: {fila[:60]}")

    def test_reverso_usa_html_y_escapa_el_codigo(self) -> None:
        """Con #html:true el reverso usa <br>, y el codigo queda escapado.

        La invariante no es "aparecenangle entities", sino que ningun `<` del
        reverso pueda ser markup no previsto: comparaciones del codigo fuente
        (`stock <= 0`) tienen que llegar como `&lt;`.
        """
        destino = self.carpeta / "anki.txt"
        resultado = ejecutar("-i", str(CODIGO_VALIDO), "--format", "anki", "-o", str(destino))
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        texto = destino.read_text(encoding="utf-8")
        self.assertIn("#html:true", texto.splitlines())
        filas = [linea for linea in texto.splitlines() if linea and not linea.startswith("#")]
        reversos = [fila.split("\t")[1] for fila in filas]
        permitidos = {"<b>", "</b>", "<br>"}
        escapadas = 0
        for reverso in reversos:
            for etiqueta in re.findall(r"<[^>]*>", reverso):
                self.assertIn(
                    etiqueta,
                    permitidos,
                    f"markup no previsto en el reverso, el codigo no esta escapado: {etiqueta}",
                )
            self.assertIn("<b>Respuesta:</b>", reverso)
            self.assertIn("<br>", reverso)
            if "&lt;" in reverso or "&gt;" in reverso:
                escapadas += 1
        self.assertGreater(
            escapadas,
            0,
            "ningun reverso escapó '<' o '>': el escapado no se está aplicando",
        )

    def test_anki_notetype_y_deck_se_emiten_solo_si_se_piden(self) -> None:
        destino = self.carpeta / "anki.txt"
        ejecutar("-i", str(CODIGO_VALIDO), "--format", "anki", "-o", str(destino))
        sin_opciones = destino.read_text(encoding="utf-8").splitlines()
        self.assertEqual([l for l in sin_opciones if l.startswith("#notetype:")], [])
        self.assertEqual([l for l in sin_opciones if l.startswith("#deck:")], [])

        ejecutar(
            "-i", str(CODIGO_VALIDO), "--format", "anki", "-o", str(destino),
            "--anki-notetype", "Basico", "--anki-deck", "code-study-flashcards",
        )
        con_opciones = destino.read_text(encoding="utf-8").splitlines()
        self.assertIn("#notetype:Basico", con_opciones)
        self.assertIn("#deck:code-study-flashcards", con_opciones)

    def test_anki_no_requiere_la_plantilla(self) -> None:
        destino = self.carpeta / "anki.txt"
        resultado = ejecutar(
            "-i", str(CODIGO_VALIDO), "--format", "anki", "-o", str(destino),
            "--template", str(self.carpeta / "no_existe.md"),
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)


class ErroresDeEntrada(BasePrueba):
    """Entradas invalidas: mensaje claro, pista y codigo de salida 3."""

    def test_archivo_inexistente(self) -> None:
        resultado = ejecutar("-i", str(self.carpeta / "no_existe.py"))
        self.assertEqual(resultado.returncode, 3)
        self.assertIn("no existe", resultado.stderr)
        self.assertIn("Sugerencia:", resultado.stderr)

    def test_archivo_vacio(self) -> None:
        resultado = ejecutar("-i", str(EJEMPLOS / "empty_sample.py"))
        self.assertEqual(resultado.returncode, 3)
        self.assertIn("vacio", resultado.stderr)

    def test_extension_no_soportada(self) -> None:
        resultado = ejecutar("-i", str(EJEMPLOS / "unsupported_sample.pdf"))
        self.assertEqual(resultado.returncode, 3)
        self.assertIn("formato no soportado", resultado.stderr)
        self.assertIn(".py", resultado.stderr)

    def test_archivo_binario(self) -> None:
        binario = self.carpeta / "corrupto.py"
        binario.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
        resultado = ejecutar("-i", str(binario))
        self.assertEqual(resultado.returncode, 3)
        self.assertIn("binario", resultado.stderr)

    def test_python_con_error_de_sintaxis(self) -> None:
        resultado = ejecutar("-i", str(EJEMPLOS / "broken_syntax_sample.py"))
        self.assertEqual(resultado.returncode, 3)
        self.assertIn("no es Python valido", resultado.stderr)

    def test_texto_sin_conceptos_reconocibles(self) -> None:
        vacio_de_contenido = self.carpeta / "vacio.md"
        vacio_de_contenido.write_text("\n\n   \n", encoding="utf-8")
        resultado = ejecutar("-i", str(vacio_de_contenido))
        self.assertEqual(resultado.returncode, 3)

    def test_carpeta_sin_formatos_soportados(self) -> None:
        carpeta = self.carpeta / "vacia"
        carpeta.mkdir()
        (carpeta / "documento.pdf").write_text("texto", encoding="utf-8")
        resultado = ejecutar("-i", str(carpeta))
        self.assertEqual(resultado.returncode, 3)
        self.assertIn("formato soportado", resultado.stderr)

    def test_argumento_obligatorio_ausente(self) -> None:
        resultado = ejecutar("-o", str(self.salida))
        self.assertEqual(resultado.returncode, 2)
        self.assertIn("--input", resultado.stderr)

    def test_lang_invalido_es_error_de_uso(self) -> None:
        resultado = ejecutar("-i", str(CODIGO_VALIDO), "--lang", "klingon")
        self.assertEqual(resultado.returncode, 2)


class ErroresDeAssets(BasePrueba):
    """Plantilla o guia incorrectas: codigo de salida 4."""

    def test_plantilla_inexistente(self) -> None:
        resultado = ejecutar(*self.combo("--template", str(self.carpeta / "no_existe.md")))
        self.assertEqual(resultado.returncode, 4)
        self.assertIn("plantilla", resultado.stderr)

    def test_plantilla_sin_tokens(self) -> None:
        plantilla = self.carpeta / "vacia.md"
        plantilla.write_text("# Tarjeta\n\n## Pregunta\n\n---\n\nalgo\n", encoding="utf-8")
        resultado = ejecutar(*self.combo("--template", str(plantilla)))
        self.assertEqual(resultado.returncode, 4)
        self.assertIn("{{PREGUNTA}}", resultado.stderr)

    def test_plantilla_sin_separador_de_tarjetas(self) -> None:
        plantilla = self.carpeta / "sin_separador.md"
        plantilla.write_text(
            "# {{TITULO}} | {{ORIGEN}} | {{TOTAL}} | {{NUMERO}} | {{CONCEPTO}} | {{TIPO}} | "
            "{{DIFICULTAD}} | {{TAGS}} | {{UBICACION}} | {{PREGUNTA}} | {{RESPUESTA}} | "
            "{{EXPLICACION}} | {{CODIGO}}",
            encoding="utf-8",
        )
        resultado = ejecutar(*self.combo("--template", str(plantilla)))
        self.assertEqual(resultado.returncode, 4)
        self.assertIn("---", resultado.stderr)

    def test_guia_inexistente(self) -> None:
        resultado = ejecutar(*self.combo("--guide", str(self.carpeta / "no_existe.md")))
        self.assertEqual(resultado.returncode, 4)
        self.assertIn("guia", resultado.stderr)

    def test_guia_con_json_invalido(self) -> None:
        guia = self.carpeta / "guia.md"
        guia.write_text(
            "<!-- active-recall-rules:start -->\n```json\n{ \"tipos\": { \"x\": {,} } }\n```\n"
            "<!-- active-recall-rules:end -->\n",
            encoding="utf-8",
        )
        resultado = ejecutar(*self.combo("--guide", str(guia)))
        self.assertEqual(resultado.returncode, 4)
        self.assertIn("invalido", resultado.stderr)

    def test_guia_sin_bloque_de_configuracion(self) -> None:
        guia = self.carpeta / "guia.md"
        guia.write_text("# Solo texto pedagogico, sin configuracion.\n", encoding="utf-8")
        resultado = ejecutar(*self.combo("--guide", str(guia)))
        self.assertEqual(resultado.returncode, 4)
        self.assertIn("configuracion", resultado.stderr)

    def test_guia_con_tipo_incompleto(self) -> None:
        guia = self.carpeta / "guia.md"
        guia.write_text(
            "<!-- active-recall-rules:start -->\n```json\n"
            '{ "reglas": [{"id": "R1", "nombre": "x"}], "tipos": {"t": {"dificultad": "facil"}} }\n'
            "```\n<!-- active-recall-rules:end -->\n",
            encoding="utf-8",
        )
        resultado = ejecutar(*self.combo("--guide", str(guia)))
        self.assertEqual(resultado.returncode, 4)
        self.assertIn("etiqueta", resultado.stderr)


class ConsistenciaDeEjecucion(BasePrueba):
    """El comportamiento determinista y el contrato de la interfaz de linea."""

    def test_es_determinista(self) -> None:
        ejecutar(*self.combo())
        primera = self.texto_salida()
        ejecutar(*self.combo())
        self.assertEqual(primera, self.texto_salida())

    def test_misma_entrada_dos_veces_misma_salida(self) -> None:
        primera_destino = self.carpeta / "a.md"
        segunda_destino = self.carpeta / "b.md"
        ejecutar("-i", str(APUNTES), "-o", str(primera_destino), "--quiet")
        ejecutar("-i", str(APUNTES), "-o", str(segunda_destino), "--quiet")
        self.assertEqual(primera_destino.read_text(encoding="utf-8"), segunda_destino.read_text(encoding="utf-8"))

    def test_version_es_1_0_0(self) -> None:
        resultado = ejecutar("--version")
        self.assertEqual(resultado.returncode, 0)
        self.assertIn("1.0.0", resultado.stdout)

    def test_ayuda_documenta_las_opciones_principales(self) -> None:
        resultado = ejecutar("--help")
        self.assertEqual(resultado.returncode, 0)
        for opcion in ("--input", "--output", "--format", "--template", "--guide", "--max-cards"):
            self.assertIn(opcion, resultado.stdout)

    def test_salida_por_defecto_en_el_directorio_actual(self) -> None:
        resultado = subprocess.run(
            [sys.executable, str(SCRIPT), "-i", "examples/input_sample.py", "--quiet"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(RAIZ_SKILL),
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertTrue((RAIZ_SKILL / "input_sample_flashcards.md").exists())
        (RAIZ_SKILL / "input_sample_flashcards.md").unlink()

    def test_max_cards_negativo_es_error_de_uso(self) -> None:
        """Un valor negativo de --max-cards debe devolver el codigo 2."""
        with tempfile.TemporaryDirectory() as temporal:
            destino = Path(temporal) / "salida.md"
            resultado = ejecutar(
                "-i", str(RAIZ_SKILL / "examples" / "input_sample.py"),
                "-o", str(destino),
                "--max-cards", "-1",
            )
        self.assertEqual(resultado.returncode, 2, resultado.stderr)
        self.assertIn("uso incorrecto", resultado.stderr)
        self.assertIn("--max-cards", resultado.stderr)
        self.assertFalse(destino.exists())

    def test_entrada_sin_conceptos_devuelve_codigo_de_entrada(self) -> None:
        """Un archivo valido pero sin conceptos debe devolver 3, no 1."""
        with tempfile.TemporaryDirectory() as temporal:
            entrada = Path(temporal) / "vacio_de_conceptos.md"
            entrada.write_text("texto plano sin estructura\n", encoding="utf-8")
            resultado = ejecutar(
                "-i", str(entrada), "-o", str(Path(temporal) / "salida.md")
            )
        self.assertEqual(resultado.returncode, 3, resultado.stderr)
        self.assertIn("ninguna tarjeta", resultado.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
