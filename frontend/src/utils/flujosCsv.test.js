import { describe, expect, it } from 'vitest';
import { parseFlujosCsv, validarFlujo } from './flujosCsv';

describe('parseFlujosCsv', () => {
  it('parsea un CSV válido con coma', () => {
    const csv = 'edge_origen,edge_destino,veh_h,pct_pesados\nE1,E2,800,10\nE3,E4,450,5.5\n';
    const r = parseFlujosCsv(csv);
    expect(r.errores).toEqual([]);
    expect(r.flujos).toHaveLength(2);
    expect(r.flujos[1]).toEqual({
      edge_origen: 'E3',
      edge_destino: 'E4',
      veh_h: 450,
      pct_pesados: 5.5,
    });
  });

  it('detecta separador ; y coma decimal', () => {
    const csv = 'origen;destino;veh/h;pesados\nE1;E2;800;12,5';
    const r = parseFlujosCsv(csv);
    expect(r.errores).toEqual([]);
    expect(r.flujos[0].pct_pesados).toBe(12.5);
  });

  it('reporta errores por fila con el número de línea del archivo', () => {
    const csv = 'edge_origen,edge_destino,veh_h,pct_pesados\nE1,E2,800,10\nE1,E1,100,0\nE5,E6,abc,200\n';
    const r = parseFlujosCsv(csv);
    expect(r.flujos).toHaveLength(1);
    expect(r.errores.map((e) => e.fila)).toEqual([3, 4]);
    expect(r.errores[0].mensaje).toMatch(/mismo edge/);
    expect(r.errores[1].mensaje).toMatch(/veh\/h/);
  });

  it('avisa cuando faltan columnas', () => {
    const r = parseFlujosCsv('edge_origen,veh_h\nE1,100');
    expect(r.flujos).toEqual([]);
    expect(r.errores[0].mensaje).toMatch(/Faltan columnas/);
  });

  it('maneja archivo vacío y BOM', () => {
    expect(parseFlujosCsv('').errores[0].mensaje).toMatch(/vacío/);
    const r = parseFlujosCsv('\uFEFFedge_origen,edge_destino,veh_h,pct_pesados\nA,B,10,0');
    expect(r.flujos).toHaveLength(1);
  });
});

describe('validarFlujo', () => {
  it('acepta un flujo correcto', () => {
    expect(
      validarFlujo({ edge_origen: 'A', edge_destino: 'B', veh_h: 100, pct_pesados: 0 }),
    ).toEqual([]);
  });
  it('rechaza veh_h <= 0', () => {
    expect(
      validarFlujo({ edge_origen: 'A', edge_destino: 'B', veh_h: 0, pct_pesados: 0 }),
    ).toContain('veh/h debe ser mayor que 0');
  });
});