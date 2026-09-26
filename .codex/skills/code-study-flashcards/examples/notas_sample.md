# Repaso: estructuras de datos en Python

Estos son apuntes de ejemplo para `code-study-flashcards`. No son codigo de la
skill: son material de estudio que la skill convierte en tarjetas.

## Listas vs tuplas

**lista** es una coleccion mutable y ordenada: se puede agregar, quitar y
cambiar elementos con `append`, `insert` o `remove`. Se usa cuando el conjunto
de datos va a cambiar.

**tupla** es inmutable y tambien ordenada. Se usa para datos fijos, y como
clave de diccionario si todos sus elementos son inmutables.

La diferencia no es de velocidad sino de intencion: si el dato no debe cambiar,
una tupla documenta esa intencion en el tipo mismo.

Pasos para elegir la estructura correcta:

- El dato cambia durante la ejecucion? -> lista
- El dato es fijo y heterogeneo? -> tupla
- Necesito pares clave-valor con busqueda rapida? -> diccionario
- Necesito unicidad y acceso por posicion? -> conjunto

## Diccionarios y claves

Un **diccionario** mapea claves a valores con complejidad de busqueda media O(1).
En Python 3.7 el orden de insercion esta garantizado, asi que `list(d.items())`
respeta el orden en que se agregaron las claves.

Dos errores habituales al trabajar con diccionarios:

- Usar `d[x]` cuando la clave puede no existir: lanza `KeyError`. Usa `d.get(x, por_defecto)`.
- Confundir el valor por defecto de `get` con un valor almacenado: `get` no inserta nada.

Ejemplo minimo:

```python
def contar_categorias(productos):
    conteo = {}
    for producto in productos:
        clave = producto.get("categoria", "sin categoria")
        conteo[clave] = conteo.get(clave, 0) + 1
    return conteo
```

## Control de flujo

`if` decide una rama; `for` recorre; `while` repite mientras la condicion sea
cierta. La diferencia clave es que `for` itera sobre un objeto iterable
(lista, cadena, diccionario) mientras `while` depende de un contador que el
programaactualiza.

El error mas comun con `while` es olvidar actualizar la condicion, lo que produce
un bucle infinito. Con `for` ese error es imposible porque el avance lo hace el
propio lenguaje.
