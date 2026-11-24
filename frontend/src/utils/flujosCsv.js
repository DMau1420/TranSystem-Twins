// Validación y parseo de flujos O-D (CU-10 y CU-21).
// Un flujo: { edge_origen, edge_destino, veh_h, pct_pesados }

export const COLUMNAS = ['edge_origen', 'edge_destino', 'veh_h', 'pct_pesados'];

// Nombres de encabezado aceptados -> columna canónica
const ALIAS = {
  edge_origen: 'edge_origen',
  origen: 'edge_origen',
  edge_destino: 'edge_destino',
  destino: 'edge_destino',
  veh_h: 'veh_h',
  vehh: 'veh_h',
  'veh/h': 'veh_h',
  vehiculos_hora: 'veh_h',
  pct_pesados: 'pct_pesados',
  pesados: 'pct_pesados',
  '%_pesados': 'pct_pesados',
  porcentaje_pesados: 'pct_pesados',
};

const normaliza = (s) =>
  s
    .replace(/^\uFEFF/, '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '_');

/** Valida un flujo ya tipado. Devuelve un arreglo de mensajes (vacío si es válido). */
export function validarFlujo(f) {
  const errores = [];
  if (!f.edge_origen || !String(f.edge_origen).trim()) errores.push('Falta edge de origen');
  if (!f.edge_destino || !String(f.edge_destino).trim()) errores.push('Falta edge de destino');
  if (
    f.edge_origen &&
    f.edge_destino &&
    String(f.edge_origen).trim() === String(f.edge_destino).trim()
  ) {
    errores.push('Origen y destino no pueden ser el mismo edge');
  }
  const veh = Number(f.veh_h);
  if (f.veh_h === '' || f.veh_h == null || !Number.isFinite(veh)) {
    errores.push('veh/h debe ser un número');
  } else if (veh <= 0) {
    errores.push('veh/h debe ser mayor que 0');
  }
  const p = Number(f.pct_pesados);
  if (f.pct_pesados === '' || f.pct_pesados == null || !Number.isFinite(p)) {
    errores.push('% pesados debe ser un número');
  } else if (p < 0 || p > 100) {
    errores.push('% pesados debe estar entre 0 y 100');
  }
  return errores;
}

// Divide una línea respetando comillas dobles.
function partirLinea(linea, sep) {
  const out = [];
  let actual = '';
  let enComillas = false;
  for (let i = 0; i < linea.length; i++) {
    const c = linea[i];
    if (c === '"') {
      if (enComillas && linea[i + 1] === '"') {
        actual += '"';
        i++;
      } else {
        enComillas = !enComillas;
      }
    } else if (c === sep && !enComillas) {
      out.push(actual);
      actual = '';
    } else {
      actual += c;
    }
  }
  out.push(actual);
  return out.map((v) => v.trim());
}

function detectaSeparador(primeraLinea) {
  const comas = (primeraLinea.match(/,/g) || []).length;
  const puntoComa = (primeraLinea.match(/;/g) || []).length;
  return puntoComa > comas ? ';' : ',';
}

/**
 * Parsea el texto de un CSV de flujos.
 * @returns {{ flujos: object[], errores: {fila:number, mensaje:string}[], totalFilas: number }}
 * `fila` es el número de línea en el archivo (el encabezado es la fila 1).
 */
export function parseFlujosCsv(texto) {
  const lineas = texto.split(/\r?\n/);
  const errores = [];
  const flujos = [];

  // Primer renglón no vacío = encabezado
  let idxEncabezado = lineas.findIndex((l) => l.trim() !== '');
  if (idxEncabezado === -1) {
    return { flujos, errores: [{ fila: 1, mensaje: 'El archivo está vacío' }], totalFilas: 0 };
  }

  const sep = detectaSeparador(lineas[idxEncabezado]);
  const encabezado = partirLinea(lineas[idxEncabezado], sep).map(
    (h) => ALIAS[normaliza(h)] ?? null,
  );

  const faltantes = COLUMNAS.filter((c) => !encabezado.includes(c));
  if (faltantes.length) {
    return {
      flujos,
      errores: [
        {
          fila: idxEncabezado + 1,
          mensaje: `Faltan columnas: ${faltantes.join(', ')}. Se esperaba: ${COLUMNAS.join(', ')}`,
        },
      ],
      totalFilas: 0,
    };
  }

  let totalFilas = 0;
  for (let i = idxEncabezado + 1; i < lineas.length; i++) {
    if (lineas[i].trim() === '') continue;
    totalFilas++;
    const celdas = partirLinea(lineas[i], sep);
    const flujo = {};
    encabezado.forEach((col, j) => {
      if (col) flujo[col] = celdas[j] ?? '';
    });

    // Acepta coma decimal (ej. "12,5") solo cuando el separador es ";"
    const aNumero = (v) => (typeof v === 'string' ? v.replace(',', '.') : v);
    flujo.veh_h = aNumero(flujo.veh_h);
    flujo.pct_pesados = aNumero(flujo.pct_pesados);

    const problemas = validarFlujo(flujo);
    if (problemas.length) {
      errores.push({ fila: i + 1, mensaje: problemas.join('; ') });
    } else {
      flujos.push({
        edge_origen: String(flujo.edge_origen).trim(),
        edge_destino: String(flujo.edge_destino).trim(),
        veh_h: Number(flujo.veh_h),
        pct_pesados: Number(flujo.pct_pesados),
      });
    }
  }

  if (totalFilas === 0) {
    errores.push({ fila: idxEncabezado + 1, mensaje: 'El archivo no tiene filas de datos' });
  }

  return { flujos, errores, totalFilas };
}