import { useId } from 'react';
import { validarFlujo } from '../../utils/flujosCsv';
import '../shared/sysBlocks.css';
import './demanda.css';

// CU-10: editor de flujos O-D. Componente controlado.
//
// Props:
//   value     [{ edge_origen, edge_destino, veh_h, pct_pesados }]
//   onChange  (nuevoArreglo) => void
//   edges     opcional, ids de edges de la red para autocompletar (datalist)
//   disabled  opcional

const FLUJO_VACIO = { edge_origen: '', edge_destino: '', veh_h: '', pct_pesados: 0 };

export default function FlujosEditor({ value = [], onChange, edges = [], disabled = false }) {
  const listId = useId();

  const actualiza = (i, campo, v) =>
    onChange(value.map((f, idx) => (idx === i ? { ...f, [campo]: v } : f)));
  const agrega = () => onChange([...value, { ...FLUJO_VACIO }]);
  const quita = (i) => onChange(value.filter((_, idx) => idx !== i));

  const totalVeh = value.reduce((acc, f) => acc + (Number(f.veh_h) || 0), 0);
  const filasConError = value.filter((f) => validarFlujo(f).length > 0).length;

  return (
    <div className="sysb flj">
      <div className="flj-head">
        <h4 className="sysb-title">// DEMANDA // FLUJOS O-D</h4>
        <button type="button" className="sysb-btn" onClick={agrega} disabled={disabled}>
          Agregar flujo
        </button>
      </div>

      {edges.length > 0 && (
        <datalist id={listId}>
          {edges.map((e) => (
            <option key={e} value={e} />
          ))}
        </datalist>
      )}

      {value.length === 0 ? (
        <p className="sysb-muted">
          Aún no hay flujos. Agrega uno a mano o carga un archivo .csv.
        </p>
      ) : (
        <div className="sysb-scroll">
          <table className="sysb-table">
            <thead>
              <tr>
                <th>Edge origen</th>
                <th>Edge destino</th>
                <th>veh/h</th>
                <th>% pesados</th>
                <th>
                  <span className="flj-sr">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {value.map((f, i) => {
                const errores = validarFlujo(f);
                const ref = `flj-err-${listId}-${i}`;
                return (
                  <tr key={i}>
                    <td>
                      <input
                        className="sysb-input"
                        list={edges.length ? listId : undefined}
                        value={f.edge_origen}
                        onChange={(e) => actualiza(i, 'edge_origen', e.target.value)}
                        aria-label={`Edge origen, fila ${i + 1}`}
                        aria-invalid={errores.length > 0}
                        aria-describedby={errores.length ? ref : undefined}
                        disabled={disabled}
                      />
                    </td>
                    <td>
                      <input
                        className="sysb-input"
                        list={edges.length ? listId : undefined}
                        value={f.edge_destino}
                        onChange={(e) => actualiza(i, 'edge_destino', e.target.value)}
                        aria-label={`Edge destino, fila ${i + 1}`}
                        aria-invalid={errores.length > 0}
                        disabled={disabled}
                      />
                    </td>
                    <td className="flj-num">
                      <input
                        className="sysb-input"
                        type="number"
                        min="1"
                        step="1"
                        value={f.veh_h}
                        onChange={(e) => actualiza(i, 'veh_h', e.target.value)}
                        aria-label={`Vehículos por hora, fila ${i + 1}`}
                        aria-invalid={errores.length > 0}
                        disabled={disabled}
                      />
                    </td>
                    <td className="flj-num">
                      <input
                        className="sysb-input"
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        value={f.pct_pesados}
                        onChange={(e) => actualiza(i, 'pct_pesados', e.target.value)}
                        aria-label={`Porcentaje de pesados, fila ${i + 1}`}
                        aria-invalid={errores.length > 0}
                        disabled={disabled}
                      />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="sysb-btn sysb-btn--danger"
                        onClick={() => quita(i)}
                        disabled={disabled}
                        aria-label={`Quitar flujo ${i + 1}`}
                      >
                        Quitar
                      </button>
                    </td>
                    {errores.length > 0 && (
                      <td id={ref} className="flj-sr">
                        {errores.join('; ')}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {value.length > 0 && (
        <p className="sysb-muted flj-foot">
          {value.length} flujos · {totalVeh.toLocaleString('es-MX')} veh/h en total
          {filasConError > 0 && (
            <span className="sysb-error">
              {' '}
              · {filasConError} con datos por corregir
            </span>
          )}
        </p>
      )}
    </div>
  );
}