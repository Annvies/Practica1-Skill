// Ejemplo de entrada para code-study-flashcards en un lenguaje sin AST estandar.
//
// A diferencia de .py, aqui el analisis es heuristico (por forma de la linea) y
// la propia tarjeta lo advierte. Sirve para comparar ambos caminos del script.

const MAX_INTENTOS = 3;
const TIMEOUT_MS = 1500;

export function validarCampos(campos) {
  if (!campos || campos.length === 0) {
    return { ok: false, errores: ["la lista de campos esta vacia"] };
  }
  const faltantes = campos.filter((campo) => !campo.trim());
  return { ok: faltantes.length === 0, errores: faltantes };
}

async function reintentar(operacion, intentos = MAX_INTENTOS) {
  for (let i = 0; i < intentos; i++) {
    try {
      return await operacion();
    } catch (error) {
      if (i === intentos - 1) throw error;
    }
  }
  return null;
}

class Carrito {
  constructor(clave) {
    this.clave = clave;
    this.items = [];
  }

  agregar(item) {
    this.items.push(item);
    return this.items.length;
  }

  vacio() {
    return this.items.length === 0;
  }
}
