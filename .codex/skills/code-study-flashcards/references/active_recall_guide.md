# Guía de Repaso Activo (Active Recall) — code-study-flashcards

Esta es la referencia pedagógica que gobierna la generación de tarjetas. **No es decorativa**:
`scripts/generate_cards.py` lee de este archivo dos cosas concretas:

1. El bloque delimitado por los marcadores `active-recall-rules:start` y
   `active-recall-rules:end` (un JSON válido dentro de un bloque cercado) para obtener la
   **taxonomía de tipos de tarjeta**, los **patrones de pregunta**
   y la **escala de dificultad** que se aplican a cada concepto extraído del código.
2. Los **ids de las reglas** (R1…R8) para etiquetar cada tarjeta con la regla que justifica su diseño,
   de modo que la tarjeta sea auditable: siempre se puede responder *"¿por qué esta pregunta?"*.

Si el archivo falta, el JSON es inválido o a un tipo de tarjeta le falta `etiqueta`/`dificultad`/`preguntas`,
el script aborta con `GuideError` (exit code 4) en vez de inventar reglas. Ver `SKILL.md` § Manejo de errores.

---

## 1. Por qué repasar leyendo no funciona

| Técnica | Qué produce el cerebro | Retención a 1 semana |
| --- | --- | --- |
| Releer los apuntes (*copies*) | **Reconocimiento**: "esto ya lo vi" | ~20 % |
| Subrayar dos veces | Reconocimiento, con sensación falsa de dominio | ~25 % |
| **Recuperación activa** (esta skill) | **Reconstrucción** desde la memoria de trabajo | ~65 % |

Copiar código genera la ilusión de saberlo: el texto está delante, entonces el cerebro no tiene que
extraerlo. Al tapar el código y reconstruir la firma, el esfuerzo de extracción es justo lo que consolida
la memoria de largo plazo. La regla operativa es simple: **el material de estudio debe tener una pregunta
que obligue a producir la respuesta antes de poder leerla.**

## 2. Reglas que aplica el generador

| Id | Regla | Cómo se implementa en el script |
| --- | --- | --- |
| R1 | **Atomicidad** — una tarjeta, un concepto | Cada tarjeta responde a una sola pregunta; el código se divide por función, parámetro, retorno, etc. |
| R2 | **Recuperación activa** — nada de copies | Ninguna tarjeta repite un bloque de código como "pregunta"; siempre se formula una pregunta |
| R3 | **Una función, varias tarjetas** | De cada función se generan hasta 4 tarjetas distintas (propósito, firma, parámetros, retorno) |
| R4 | **Preguntar el porqué** | Los tipos de control de flujo preguntan por la *decisión*, no por la sintaxis |
| R5 | **Autopista: con tenacidad, no con fuerza** | Se marcan los huecos (`gap`) del código sin documentar: son lo primero que hay que atacar |
| R6 | **Contexto mínimo + original** | La respuesta da el mínimo y el collapsible guarda el código original para verificar |
| R7 | **Etiquetado** | Cada tarjeta lleva tags (`funcion`, `py`, `dificil`…) para filtrar y priorizar sesiones |
| R8 | **Auditable** | Cada tarjeta registra qué regla justifica su diseño |

## 3. Taxonomía de tarjetas

Siete familias de conocimiento de código, con el nivel de dificultad que el generador asigna:

1. **Propósito** — qué hace la unidad y qué devuelve (no cómo lo hace).
2. **Contrato** — firma, parámetros, tipos, valores por defecto.
3. **Resultado** — qué devuelve exactamente en cada camino.
4. **Estructura** — cómo se modela la solución (atributos, constantes, dependencias).
5. **Decisión** — qué condiciones/bucles usa el código y por qué.
6. **Notas** — conceptos de apuntes en Markdown, sin código.
7. **Hueco** — el código no documenta algo y el estudiante lo adivina (**gap card**, R5).

## 4. Cómo escribir la pregunta (heurística del generador)

Al elegir el patrón de pregunta, el script toma **el primero cuyo contexto esté disponible**, de modo que
nunca imprime un `{}` vacío:

1. Patrón específico y respondible (requiere contexto → `./files.py:12`).
2. Patrón genérico con el nombre del concepto (`{{nombre}}`).
3. Patrón de último recurso, sin marcadores.

Nunca se genera una pregunta que se conteste con un "sí" o un "no": son fallos de diseño de tarjeta,
no pruebas de memoria. Si la respuesta cabe en una frase, la pregunta cabe en una frase.

## 5. Sesión de repaso recomendada (fuera del script, para el estudiante)

1. Ordenar por dificultad: `gap` y `dificil` primero.
2. Intentar responder **antes** de desplegar la respuesta (R2).
3. Fallar está bien; lo que cuenta es el *intento de recuperación*. Marcar como fallada y volver en 48 h.
4. Una función dominada = todas sus tarjetas respondidas sin mirar. Recién ahí pasar a la siguiente.

---

## 6. Configuración machine-readable (leída por `generate_cards.py`)

Marcadores requeridos: `<!-- active-recall-rules:start -->` y `<!-- active-recall-rules:end -->`.
Cada tipo en `tipos` **debe** tener `etiqueta`, `dificultad` (facil|media|dificil), `tags` y al menos un
patrón en `preguntas`. Marcadores disponibles en los patrones: `{{nombre}}`, `{{archivo}}`, `{{linea}}`,
`{{tipo}}`, `{{detalle}}`, `{{contexto}}`. Los marcadores ausentes en el contexto se descartan al elegir patrón.

<!-- active-recall-rules:start -->
```json
{
  "version": "1.0",
  "idioma": "es",
  "reglas": [
    { "id": "R1", "nombre": "Atomicidad", "descripcion": "Una tarjeta responde a un solo concepto." },
    { "id": "R2", "nombre": "Recuperacion activa", "descripcion": "No copies: la pregunta exige producir la respuesta." },
    { "id": "R3", "nombre": "Una funcion, varias tarjetas", "descripcion": "Proposito, firma, parametros y retorno son tarjetas distintas." },
    { "id": "R4", "nombre": "Preguntar el porque", "descripcion": "Se pregunta por la decision, no por la sintaxis." },
    { "id": "R5", "nombre": "Gap cards", "descripcion": "Lo no documentado se marca como hueco y se ataca primero." },
    { "id": "R6", "nombre": "Contexto minimo", "descripcion": "Respuesta minima en el anverso, codigo original en el plegable." },
    { "id": "R7", "nombre": "Etiquetado", "descripcion": "Tags por familia y dificultad para filtrar la sesion." },
    { "id": "R8", "nombre": "Auditable", "descripcion": "Cada tarjeta declara la regla que justifica su diseno." }
  ],
  "tipos": {
    "funcion_proposito": {
      "etiqueta": "Proposito de funcion",
      "icono": "objetivo",
      "dificultad": "media",
      "tags": ["funcion", "proposito"],
      "reglas": ["R1", "R2", "R3"],
      "preguntas": [
        "Sin mirar el codigo: que hace `{{nombre}}` y que devuelve? Respondelo con tus palabras antes de continuar.",
        "Cual es la responsabilidad de `{{nombre}}`? Explicala sin leer la implementacion."
      ]
    },
    "funcion_firma": {
      "etiqueta": "Firma y contrato",
      "icono": "contrato",
      "dificultad": "media",
      "tags": ["funcion", "contrato"],
      "reglas": ["R1", "R3"],
      "preguntas": [
        "Escribe la firma completa de `{{nombre}}` (nombre, parametros y tipos de retorno) de memoria.",
        "Como se llama `{{nombre}}` y de donde vive? Indica la ruta y el numero de linea."
      ]
    },
    "funcion_parametros": {
      "etiqueta": "Parametros",
      "icono": "parametros",
      "dificultad": "dificil",
      "tags": ["funcion", "parametros"],
      "reglas": ["R1", "R3"],
      "preguntas": [
        "Cuales son los parametros de `{{nombre}}`, que tipo espera cada uno y cual es su valor por defecto?",
        "Que parametro de `{{nombre}}` es obligatorio y cual es opcional? Explica como se distinguen."
      ]
    },
    "funcion_retorno": {
      "etiqueta": "Valor de retorno",
      "icono": "retorno",
      "dificultad": "dificil",
      "tags": ["funcion", "retorno"],
      "reglas": ["R1", "R3", "R4"],
      "preguntas": [
        "Que devuelve exactamente `{{nombre}}`? Indica la expresion o el valor de cada `return`.",
        "En que camino de `{{nombre}}` se sale antes de tiempo y con que valor se sale?"
      ]
    },
    "funcion_sin_docstring": {
      "etiqueta": "Hueco de documentacion",
      "icono": "gap",
      "dificultad": "dificil",
      "tags": ["gap", "documentacion"],
      "reglas": ["R5", "R2"],
      "preguntas": [
        "`{{nombre}}` no tiene docstring. Sin leer su cuerpo: que crees que hace y que devuelve?",
        "Escribe la docstring que le falta a `{{nombre}}`."
      ]
    },
    "clase_constructor": {
      "etiqueta": "Constructor e inicializacion",
      "icono": "pila",
      "dificultad": "media",
      "tags": ["clase", "constructor"],
      "reglas": ["R1", "R3"],
      "preguntas": [
        "Que atributos deja inicializados `{{nombre}}` al construir un objeto? Lista todos con su valor inicial.",
        "Escribe el `__init__` de `{{nombre}}` de memoria, con sus parametros y sus valores por defecto."
      ]
    },
    "clase_atributos": {
      "etiqueta": "Estado de la clase",
      "icono": "paquete",
      "dificultad": "dificil",
      "tags": ["clase", "estado"],
      "reglas": ["R1", "R4"],
      "preguntas": [
        "Que estado guarda la clase `{{nombre}}`? Explica para que sirve cada atributo.",
        "Que atributo de `{{nombre}}` se modifica con mas frecuencia y por que?"
      ]
    },
    "clase_metodos": {
      "etiqueta": "Metodos publicos",
      "icono": "ruta",
      "dificultad": "media",
      "tags": ["clase", "metodos"],
      "reglas": ["R1", "R3"],
      "preguntas": [
        "Que metodospublicos expone `{{nombre}}` y que efecto tiene cada uno sobre su estado?",
        "Enumera los metodos de `{{nombre}}` sin mirar el codigo y di cuales son privados."
      ]
    },
    "constante_modulo": {
      "etiqueta": "Constantes y configuracion",
      "icono": "numeros",
      "dificultad": "facil",
      "tags": ["constante", "configuracion"],
      "reglas": ["R1", "R2"],
      "preguntas": [
        "Que valor tiene `{{nombre}}` en `{{archivo}}` y para que se usa?",
        "Cuales son las constantes definidas en `{{archivo}}` y que valor tiene cada una?"
      ]
    },
    "dependencia_import": {
      "etiqueta": "Dependencias",
      "icono": "libros",
      "dificultad": "facil",
      "tags": ["dependencia", "libreria"],
      "reglas": ["R1", "R2"],
      "preguntas": [
        "Que importaste `{{nombre}}` y que capacidad te da?",
        "De que librerias o modulos depende `{{archivo}}` y para que se usa cada uno?"
      ]
    },
    "flujo_control": {
      "etiqueta": "Flujo de control",
      "icono": "cruce",
      "dificultad": "dificil",
      "tags": ["flujo", "logica"],
      "reglas": ["R1", "R4"],
      "preguntas": [
        "Que decisiones de control de flujo toma `{{nombre}}` y bajo que condicion se cumple cada una?",
        "Describe el recorrido de `{{nombre}}`: cuantas veces itera, cuando sale del bucle y que devuelve en cada rama."
      ]
    },
    "nota_seccion": {
      "etiqueta": "Seccion de apuntes",
      "icono": "documento",
      "dificultad": "media",
      "tags": ["notas", "concepto"],
      "reglas": ["R1", "R2"],
      "preguntas": [
        "Sin volver a tus apuntes: resume que explica la seccion **{{nombre}}** y da un ejemplo propio.",
        "Que idea principal quieres retener de la seccion **{{nombre}}**? Explicala con tus palabras."
      ]
    },
    "nota_termino": {
      "etiqueta": "Termino clave",
      "icono": "letra",
      "dificultad": "facil",
      "tags": ["notas", "termino"],
      "reglas": ["R1", "R2"],
      "preguntas": [
        "Define **{{nombre}}** con tus palabras y da un ejemplo de codigo donde se use.",
        "Como se relacionan **{{nombre}}** y el resto de conceptos de `{{archivo}}`?"
      ]
    },
    "nota_lista": {
      "etiqueta": "Lista de apuntes",
      "icono": "lista",
      "dificultad": "media",
      "tags": ["notas", "lista"],
      "reglas": ["R1", "R2", "R7"],
      "preguntas": [
        "Enumera los puntos que aparecen en la lista de **{{nombre}}**, sin mirar los apuntes.",
        "De la lista de **{{nombre}}**, cual es el punto que mas costaria explicar en un examen y por que?"
      ]
    },
    "codigo_en_notas": {
      "etiqueta": "Codigo embebido en apuntes",
      "icono": "pieza",
      "dificultad": "media",
      "tags": ["notas", "codigo"],
      "reglas": ["R1", "R3", "R6"],
      "preguntas": [
        "Reescribe el bloque de codigo de la seccion **{{nombre}}** sin mirar los apuntes.",
        "Que resuelve ese bloque? Explica la logica paso a paso en voz alta."
      ]
    }
  },
  "formato_anki": {
    "separador": "\t",
    "columnas": ["front", "back", "tags"]
  }
}
```
<!-- active-recall-rules:end -->

## 7. Mantenimiento

Al cambiar la taxonomía: edita el JSON de arriba, ejecuta `scripts/demo.sh`, y confirma que
`tests/test_generate_cards.py` sigue en verde. Si añades un tipo nuevo, el script lo usa automáticamente:
no hay listas de tipos hardcodeadas en el `.py`.
