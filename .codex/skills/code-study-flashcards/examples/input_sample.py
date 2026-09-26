"""Ejemplo de entrada para code-study-flashcards.

Este archivo NO es parte de la skill: es material de estudio. Al apuntar la
skill a este archivo se obtienen tarjetas de repaso activo de cada funcion,
clase, constante y control de flujo.

Dominio: un inventario pequeno de una tienda.
"""

import json
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

MONEDA = "BOB"
IMPUESTO = 0.13
STOCK_MINIMO = 5
PRECIOS_MAXIMOS = {"teclado": 450, "monitor": 1800, "mouse": 260}


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


def precio_con_impuesto(precio: float, aplica_descuento: bool = False) -> float:
    return round(precio * (1 + IMPUESTO) * 0.9, 2) if aplica_descuento else round(precio * (1 + IMPUESTO), 2)


def etiqueta_stock(producto: Dict) -> str:
    nombre = producto.get("nombre", "producto sin nombre")
    stock = producto.get("stock", 0)
    if stock <= 0:
        estado = "agotado"
    elif stock < STOCK_MINIMO:
        estado = "poco"
    else:
        estado = "disponible"
    return f"{nombre}: {estado} ({stock} unidades, {MONEDA})"


@dataclass
class Producto:
    nombre: str
    categoria: str
    precio: float
    stock: int = 0
    etiquetas: List[str] = field(default_factory=list)

    def disponibles(self) -> bool:
        """Indica si el producto supera el stock minimo de la tienda."""
        return self.stock >= STOCK_MINIMO

    def resumen(self) -> str:
        return f"{self.nombre} ({self.categoria}) - {self.precio} {MONEDA}"


class Inventario:
    def __init__(self, nombre: str, productos: Optional[Iterable[Producto]] = None) -> None:
        self.nombre = nombre
        self.productos: List[Producto] = list(productos or [])
        self.ultima_actualizacion = ""

    def agregar(self, producto: Producto) -> bool:
        for existente in self.productos:
            if existente.nombre == producto.nombre:
                existente.stock += producto.stock
                return False
        self.productos.append(producto)
        self.ultima_actualizacion = f"agregado: {producto.nombre}"
        return True

    def total_unidades(self) -> int:
        """Suma el stock de todos los productos del inventario."""
        return sum(producto.stock for producto in self.productos)

    def por_categoria(self) -> Dict[str, int]:
        return resumen_inventario(
            [{"nombre": p.nombre, "categoria": p.categoria} for p in self.productos]
        )

    def a_json(self) -> str:
        datos = {
            "nombre": self.nombre,
            "productos": [
                {"nombre": p.nombre, "categoria": p.categoria, "stock": p.stock}
                for p in self.productos
            ],
        }
        return json.dumps(datos, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    inv = Inventario("Tienda Tech")
    inv.agregar(Producto("Teclado", "perifericos", 350, 12))
    print(inv.a_json())
