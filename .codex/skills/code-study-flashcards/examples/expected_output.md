# Resultado esperado (expected output)

Salida real de `examples/input_sample.py` con la version 1.0.0 de la skill. Sirve como referencia
para comparar una ejecucion nueva: si cambia el numero de tarjetas o la estructura de una tarjeta,
algo se rompio.

```bash
python scripts/generate_cards.py -i examples/input_sample.py -o output/demo.md
```

## 1. Resumen en la terminal

```text
----------------------------------------------------------------
 code-study-flashcards 1.0.0  |  42 tarjetas generadas
----------------------------------------------------------------
 Entrada   examples/input_sample.py (py, 3.5 KB, 42 tarjetas)
   -   9  Parametros (funcion_parametros)
   -   9  Valor de retorno (funcion_retorno)
   -   6  Flujo de control (flujo_control)
   -   6  Hueco de documentacion (funcion_sin_docstring)
   -   4  Constantes y configuracion (constante_modulo)
   -   3  Proposito de funcion (funcion_proposito)
   -   2  Constructor e inicializacion (clase_constructor)
   -   2  Metodos publicos (clase_metodos)
   -   1  Estado de la clase (clase_atributos)
 Reglas    R1 Atomicidad, R2 Recuperacion activa, R3 Una funcion, varias tarjetas, R4 Preguntar el porque, R5 Gap cards
 Salida    output/demo.md
----------------------------------------------------------------
 Siguiente paso: responde cada tarjeta SIN leer la respuesta; despues compara.
```

## 2. Encabezado del archivo generado

````markdown
---
generado_por: code-study-flashcards
version_skill: 1.0.0
fecha: "2026-09-25"
origen: "examples/input_sample.py"
lenguaje: "py"
total_tarjetas: 42
reglas: "R1 Atomicidad, R2 Recuperacion activa, R3 Una funcion, varias tarjetas, R4 Preguntar el porque, R5 Gap cards"
---

# Repaso activo de input_sample.py

> Generado con la skill **code-study-flashcards** a partir de `examples/input_sample.py`.
> Reglas aplicadas: R1 Atomicidad, R2 Recuperacion activa, R3 Una funcion, varias tarjetas, R4 Preguntar el porque, R5 Gap cards
> Tarjetas generadas: **42** | Fecha: 2026-09-25

---
````

## 3. Una tarjeta completa (la 5 de 42, tal cual)

````markdown
## Tarjeta 5 — resumen_inventario

| Campo | Valor |
| --- | --- |
| Tipo | Proposito de funcion |
| Dificultad | media |
| Etiquetas | funcion, proposito, python, media |
| Ubicación | `examples/input_sample.py:20` |

### Pregunta

Sin mirar el codigo: que hace `resumen_inventario` y que devuelve? Respondelo con tus palabras antes de continuar.

### Respuesta

Devuelve un conteo de productos por categoria, limitado a `limite` entradas. Firma: `resumen_inventario(productos: List[Dict], limite: int = 10) -> Dict[str, int]`

### Explicación

- Firma completa: `resumen_inventario(productos: List[Dict], limite: int = 10) -> Dict[str, int]`
- Devuelve 1 forma(s) distinta(s): `dict(ordenadas[:limite])`
- La docstring tiene 8 lineas; la respuesta usa solo la frase resumen.
- Complejidad aproximada: 3 (1 + ramas + returns).
- Ubicacion: examples/input_sample.py:20

```python
def resumen_inventario(productos: List[Dict], limite: int = 10) -> Dict[str, int]:
    """Devuelve un conteo de productos por categoria, limitado a `limite` entradas.

    Args:
        productos: lista de diccionarios con las claves "nombre" y "categoria".
        limite: maximo de categorias devueltas; las demas se descartan.

    Returns:
        Un diccionario categoria -> cantidad de productos.
    """
    conteo: Dict[str, int] = {}
    for producto in productos:
        categoria = producto.get("categoria", "sin categoria").lower().strip()
        conteo[categoria] = conteo.get(categoria, 0) + 1
... (+2 lineas)
```

<details>
<summary>Ver código original completo</summary>

```python
def resumen_inventario(productos: List[Dict], limite: int = 10) -> Dict[str, int]:
    """Devuelve un conteo de productos por categoria, limitado a `limite` entradas.

    Args:
        productos: lista de diccionarios con las claves "nombre" y "categoria".
        limite: maximo de categorias devueltas; las demas se descartan.

    Returns:
        Un diccionario categoria -> cantidad de productos.
    """
    conteo: Dict[str, int] = {}
    for producto in productos:
        categoria = producto.get("categoria", "sin categoria").lower().strip()
        conteo[categoria] = conteo.get(categoria, 0) + 1
    ordenadas = sorted(conteo.items(), key=lambda par: (-par[1], par[0]))
    return dict(ordenadas[:limite])
```

</details>

<!--
Tarjeta 5 de 42 | tipo=Proposito de funcion | icono=objetivo | dificultad=media | tags=funcion, proposito, python, media
Reglas aplicadas (references/active_recall_guide.md): R1, R2, R3
Regla principal: R1 Atomicidad
-->

---
````

## 4. Las 42 tarjetas generadas

| # | Concepto | Tipo | Dificultad |
| --- | --- | --- | --- |
| 1 | `MONEDA` | Constantes y configuracion | facil |
| 2 | `IMPUESTO` | Constantes y configuracion | facil |
| 3 | `STOCK_MINIMO` | Constantes y configuracion | facil |
| 4 | `PRECIOS_MAXIMOS` | Constantes y configuracion | facil |
| 5 | `resumen_inventario` | Proposito de funcion | media |
| 6 | `resumen_inventario` | Parametros | dificil |
| 7 | `resumen_inventario` | Valor de retorno | dificil |
| 8 | `resumen_inventario` | Flujo de control | dificil |
| 9 | `precio_con_impuesto` | Hueco de documentacion | dificil |
| 10 | `precio_con_impuesto` | Parametros | dificil |
| 11 | `precio_con_impuesto` | Valor de retorno | dificil |
| 12 | `etiqueta_stock` | Hueco de documentacion | dificil |
| 13 | `etiqueta_stock` | Parametros | dificil |
| 14 | `etiqueta_stock` | Valor de retorno | dificil |
| 15 | `etiqueta_stock` | Flujo de control | dificil |
| 16 | `Producto` | Constructor e inicializacion | dificil |
| 17 | `Producto` | Estado de la clase | dificil |
| 18 | `Producto` | Metodos publicos | media |
| 19 | `Producto.disponibles` | Proposito de funcion | media |
| 20 | `Producto.disponibles` | Parametros | dificil |
| 21 | `Producto.disponibles` | Valor de retorno | dificil |
| 22 | `Producto.resumen` | Hueco de documentacion | dificil |
| 23 | `Producto.resumen` | Parametros | dificil |
| 24 | `Producto.resumen` | Valor de retorno | dificil |
| 25 | `Inventario` | Constructor e inicializacion | media |
| 26 | `Inventario` | Metodos publicos | dificil |
| 27 | `Inventario.agregar` | Hueco de documentacion | dificil |
| 28 | `Inventario.agregar` | Parametros | dificil |
| 29 | `Inventario.agregar` | Valor de retorno | dificil |
| 30 | `Inventario.agregar` | Flujo de control | dificil |
| 31 | `Inventario.total_unidades` | Proposito de funcion | media |
| 32 | `Inventario.total_unidades` | Parametros | dificil |
| 33 | `Inventario.total_unidades` | Valor de retorno | dificil |
| 34 | `Inventario.total_unidades` | Flujo de control | dificil |
| 35 | `Inventario.por_categoria` | Hueco de documentacion | dificil |
| 36 | `Inventario.por_categoria` | Parametros | dificil |
| 37 | `Inventario.por_categoria` | Valor de retorno | dificil |
| 38 | `Inventario.por_categoria` | Flujo de control | dificil |
| 39 | `Inventario.a_json` | Hueco de documentacion | dificil |
| 40 | `Inventario.a_json` | Parametros | dificil |
| 41 | `Inventario.a_json` | Valor de retorno | dificil |
| 42 | `Inventario.a_json` | Flujo de control | dificil |

## 5. Export a Anki (mismo archivo, `--format anki`)

Cuatro lineas de cabecera y despues un registro por linea: `anverso<TAB>reverso<TAB>etiquetas`.

```text
#separator:Tab
#html:false
#columns:front	back	tags
#tags column:3
Que valor tiene `MONEDA` en `examples/input_sample.py` y para que se usa?	Respuesta: MONEDA = 'BOB' | Explicacion: - Constante de modulo (NOMBRE_EN_MAYUSCULAS). - Valor: `'BOB'` - Ubicacion: examples/input_sample.py:14	constante,configuracion,python,facil,regla_R1
Que valor tiene `IMPUESTO` en `examples/input_sample.py` y para que se usa?	Respuesta: IMPUESTO = 0.13 | Explicacion: - Constante de modulo (NOMBRE_EN_MAYUSCULAS). - Valor: `0.13` - Ubicacion: examples/input_sample.py:15	constante,configuracion,python,facil,regla_R1
```

## 6. Salida de los errores controlados

```text
[ERROR: formato no soportado] Formato no soportado para 'unsupported_sample.pdf' (extension '.pdf').
  Sugerencia: codigo: .c, .cc, .cjs, .cpp, .cs, .go, .h, .hpp, .java, .js, .jsx, .kt, .mjs, .php, .py, .rb, .rs, .scala, .sql, .swift, .ts, .tsx
notas : .markdown, .md, .rst, .txt
otros : usa --lang py|js|ts|java|c|cpp|cs|php|go|rb|rs|sql|text para forzar el analisis
```

## 7. Ejemplo en TypeScript (`examples/input_sample.ts`)

Mismo contrato, pero por el extractor heuristico. Se declara el aviso y todas las
tarjetas quedan marcadas como `heuristico`.

```text
----------------------------------------------------------------
 code-study-flashcards 1.0.0  |  14 tarjetas generadas
----------------------------------------------------------------
 Entrada   examples/input_sample.ts (ts, 2.2 KB, 14 tarjetas)
   -   8  Proposito de funcion (funcion_proposito)
   -   3  Estado de la clase (clase_atributos)
   -   2  Constantes y configuracion (constante_modulo)
   -   1  Flujo de control (flujo_control)
 Reglas    R1 Atomicidad, R2 Recuperacion activa, R3 Una funcion, varias tarjetas, R4 Preguntar el porque
 Avisos
   ! input_sample.ts: analisis heuristico: no hay AST estandar para typescript en la libreria estandar.
 Salida    output/input_sample.ts_flashcards.md
----------------------------------------------------------------
```

Las 14 tarjetas, en orden:

| # | Concepto | Tipo | Que forma del codigo ejercita |
| --- | --- | --- | --- |
| 1 | `Repuesto` | Estado de la clase | `export interface` |
| 2 | `RepositorioRepuestos` | Estado de la clase | `export interface` |
| 3 | `findAll` | Proposito de funcion | Firma **sin cuerpo** en una interfaz, con tipo `Promise<...>` |
| 4 | `findById` | Proposito de funcion | Firma sin cuerpo con tipo unión `Repuesto \| null` |
| 5 | `RepuestosService` | Estado de la clase | `export class` |
| 6 | `DIAS_ROTACION_LENTA` | Constantes y configuracion | `static readonly` |
| 7 | `MAX_POR_PAGINA` | Constantes y configuracion | `static readonly` |
| 8 | `constructor` | Proposito de funcion | Inyeccion de dependencias: `constructor(private readonly repositorio: ...) {}` |
| 9 | `findAll` | Proposito de funcion | `async` con tipo de retorno generico |
| 10 | `buscarPorCodigo` | Proposito de funcion | `async` con tipo de retorno |
| 11 | `registrarAjuste` | Proposito de funcion | **Firma partida en varias lineas** |
| 12 | `resumir` | Proposito de funcion | `private` con parametro de tipo objeto |
| 13 | `ordenarPorRotacion` | Proposito de funcion | `export function` |
| 14 | el archivo | Flujo de control | Conteo heuristico de `if` |

Que **no** aparece, aunque este en el archivo: las llamadas
`this.repositorio.findAll(...)`, `this.findAll(...)` y `Math.min(...)`. Son
expresiones, no declaraciones, y una tarjeta por cada llamada llenaria el material
de ruido.
