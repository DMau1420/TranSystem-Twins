import { useRef, useState } from 'react';
import { COLUMNAS, parseFlujosCsv } from '../../utils/flujosCsv';
import '../shared/sysBlocks.css';
import './demanda.css';

// CU-21: carga de flujos O-D desde un archivo .csv.
// Muestra un reporte de errores por fila e importa solo las filas válidas.
//
// Props:
//   onImportar(flujos)  recibe [{ edge_origen, edge_destino, veh_h, pct_pesados }]
//   maxBytes            tamaño máximo del archivo (default 2 MB)

const MAX_ERRORES_VISIBLES = 50;

export default function CsvFlujosUploader({ onImportar, maxBytes = 2 * 1024 * 1024 }) {
  const inputRef = useRef(null);
  const [arrastrando, setArrastrando] = useState(false);
  const [nombre, setNombre] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [errorArchivo, setErrorArchivo] = useState(null);

  const procesar = async (archivo) => {
    setErrorArchivo(null);
    setResultado(null);
    if (!archivo) return;
    if (!/\.csv$/i.test(archivo.name)) {
      setErrorArchivo('El archivo debe tener extensión .csv.');
      return;
    }
    if (archivo.size > maxBytes) {
      setErrorArchivo(`El archivo pesa más de ${Math.round(maxBytes / 1024 / 1024)} MB.`);
      return;
    }
    try {
      const texto = await archivo.text();
      setNombre(archivo.name);
      setResultado(parseFlujosCsv(texto));
    } catch {
      setErrorArchivo('No se pudo leer el archivo.');
    }
  };

  const limpiar = () => {
    setNombre(null);
    setResultado(null);
    setErrorArchivo(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const importar = () => {
    if (!resultado?.flujos.length) return;
    onImportar?.(resultado.flujos);
    limpiar();
  };

  return (
    <div className="sysb csvu">
      <h4 className="sysb-title">// DEMANDA // CARGAR CSV</h4>

      <div
        className={`csvu-drop${arrastrando ? ' csvu-drop--on' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setArrastrando(true);
        }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => {
          e.preventDefault();
          setArrastrando(false);
          procesar(e.dataTransfer.files?.[0]);
        }}
      >
        <p className="sysb-muted" style={{ margin: '0 0 8px' }}>
          Arrastra un archivo .csv aquí o elígelo desde tu equipo.
          <br />
          Columnas: {COLUMNAS.join(', ')}
        </p>
        <button type="button" className="sysb-btn" onClick={() => inputRef.current?.click()}>
          Elegir archivo
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          hidden
          onChange={(e) => procesar(e.target.files?.[0])}
        />
      </div>

      {errorArchivo && (
        <p role="alert" className="sysb-error">
          {errorArchivo}
        </p>
      )}

      {resultado && (
        <div className="csvu-report" aria-live="polite">
          <p style={{ margin: '8px 0' }}>
            <strong>{nombre}</strong>: {resultado.flujos.length} de {resultado.totalFilas} filas
            válidas
            {resultado.errores.length > 0 && (
              <span className="sysb-warn"> · {resultado.errores.length} con errores</span>
            )}
          </p>

          {resultado.errores.length > 0 && (
            <div className="sysb-scroll csvu-errors">
              <table className="sysb-table">
                <thead>
                  <tr>
                    <th>Fila</th>
                    <th>Problema</th>
                  </tr>
                </thead>
                <tbody>
                  {resultado.errores.slice(0, MAX_ERRORES_VISIBLES).map((e, i) => (
                    <tr key={`${e.fila}-${i}`}>
                      <td>{e.fila}</td>
                      <td className="sysb-error">{e.mensaje}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {resultado.errores.length > MAX_ERRORES_VISIBLES && (
                <p className="sysb-muted">
                  Se muestran los primeros {MAX_ERRORES_VISIBLES} errores de{' '}
                  {resultado.errores.length}.
                </p>
              )}
            </div>
          )}

          <div className="csvu-actions">
            <button
              type="button"
              className="sysb-btn"
              onClick={importar}
              disabled={resultado.flujos.length === 0}
            >
              {resultado.errores.length > 0
                ? `Importar ${resultado.flujos.length} filas válidas`
                : `Importar ${resultado.flujos.length} flujos`}
            </button>
            <button type="button" className="sysb-btn" onClick={limpiar}>
              Descartar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}