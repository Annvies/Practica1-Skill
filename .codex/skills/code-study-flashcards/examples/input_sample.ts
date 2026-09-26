/**
 * Servicio de ejemplo con las convenciones tipicas de NestJS + Prisma.
 *
 * Sirve como fixture del extractor heuristico: TypeScript no tiene AST en la
 * stdlib de Python, asi que las tarjetas se generan por forma de la linea.
 * Incluye a proposito los casos que rompen los extractores ingenuos:
 *   - constante de clase con `static readonly`
 *   - constructor con modificador de acceso e inyeccion de dependencias
 *   - metodos async con tipo de retorno generico
 *   - firmas partidas en varias lineas por parametros tipo objeto
 *   - interfaz con firmas sin cuerpo
 */

import { Injectable, NotFoundException } from '@nestjs/common';

export interface Repuesto {
  id: string;
  codigo: string;
  nombre: string;
  stockFisico: number;
}

export interface RepositorioRepuestos {
  findAll(limite: number): Promise<Repuesto[]>;
  findById(id: string): Promise<Repuesto | null>;
}

@Injectable()
export class RepuestosService {
  // RN-05: un repuesto se considera de rotacion lenta si no se movio en este plazo.
  static readonly DIAS_ROTACION_LENTA = 60;
  static readonly MAX_POR_PAGINA = 100;

  constructor(private readonly repositorio: RepositorioRepuestos) {}

  async findAll(limite: number): Promise<Repuesto[]> {
    const tope = Math.min(limite, RepuestosService.MAX_POR_PAGINA);
    return this.repositorio.findAll(tope);
  }

  async buscarPorCodigo(codigo: string): Promise<Repuesto> {
    const repuestos = await this.findAll(RepuestosService.MAX_POR_PAGINA);
    const encontrado = repuestos.find((item) => item.codigo === codigo);
    if (!encontrado) {
      throw new NotFoundException(`No existe el repuesto ${codigo}`);
    }
    return encontrado;
  }

  async registrarAjuste(
    id: string,
    delta: number,
  ): Promise<Repuesto> {
    const actual = await this.repositorio.findById(id);
    if (!actual) throw new NotFoundException(`No existe el repuesto ${id}`);
    return { ...actual, stockFisico: actual.stockFisico + delta };
  }

  private resumir(repuesto: {
    id: string;
    codigo: string;
    stockFisico: number;
  }): string {
    return `${repuesto.codigo}: ${repuesto.stockFisico} unidades`;
  }
}

export function ordenarPorRotacion(repuestos: Repuesto[]): Repuesto[] {
  return [...repuestos].sort((a, b) => a.stockFisico - b.stockFisico);
}
