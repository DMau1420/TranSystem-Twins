import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { COLORES } from '../../utils/sumoNetwork';
import './MapLegend.css';

// Línea sólida de un color; `grosor` en px, `opacidad` para distinguir calle de vía principal.
const Linea = ({ color, grosor = 4, opacidad = 1 }) => (
  <i className="maplegend__linea" style={{ background: color, height: grosor, opacity: opacidad }} />
);

const Rampa = () => (
  <i
    className="maplegend__linea"
    style={{
      height: 4,
      background: `repeating-linear-gradient(90deg, ${COLORES.rampa} 0 4px, transparent 4px 8px)`,
    }}
  />
);

const Punto = () => <i className="maplegend__punto" style={{ background: COLORES.semaforo }} />;

const ITEMS = [
  { swatch: <Linea color={COLORES.principal} grosor={5} />, texto: 'Vía principal' },
  { swatch: <Linea color={COLORES.calle} grosor={3} opacidad={0.5} />, texto: 'Calle' },
  { swatch: <Rampa />, texto: 'Rampa o enlace' },
  { swatch: <Punto />, texto: 'Semáforo' },
  { swatch: <Linea color={COLORES.modificada} grosor={5} />, texto: 'Modificada en este escenario' },
  { swatch: <Linea color={COLORES.seleccion} grosor={5} />, texto: 'Seleccionada' },
];

/**
 * Simbología de la red vial. Se ancla abajo a la izquierda del MAPA (no de la pantalla),
 * así que cuando el sidebar se contrae y el mapa se ensancha, la leyenda se queda pegada a su lado.
 * Colócala dentro del <MapContainer> o dentro del contenedor del mapa (position: relative).
 */
export default function MapLegend({ visible = true }) {
  const ref = useRef(null);
  const [abierta, setAbierta] = useState(true);

  // Que los clics y el scroll sobre la leyenda no muevan ni disparen nada en el mapa.
  useEffect(() => {
    if (!ref.current) return;
    L.DomEvent.disableClickPropagation(ref.current);
    L.DomEvent.disableScrollPropagation(ref.current);
  }, [visible]);

  if (!visible) return null;

  return (
    <aside ref={ref} className="maplegend" aria-label="Simbología del mapa">
      <button
        type="button"
        className="maplegend__header"
        onClick={() => setAbierta((v) => !v)}
        aria-expanded={abierta}
      >
        <span>{'// SIMBOLOGÍA //'}</span>
        <span className="maplegend__chev" aria-hidden="true">{abierta ? '−' : '+'}</span>
      </button>

      {abierta && (
        <ul className="maplegend__lista">
          {ITEMS.map((it) => (
            <li key={it.texto}>
              <span className="maplegend__swatch">{it.swatch}</span>
              <span>{it.texto}</span>
            </li>
          ))}
          <li className="maplegend__carriles">
            <span className="maplegend__swatch maplegend__swatch--multi">
              <Linea color={COLORES.principal} grosor={3} />
              <Linea color={COLORES.principal} grosor={5} />
              <Linea color={COLORES.principal} grosor={7} />
            </span>
            <span>Grosor = número de carriles</span>
          </li>
        </ul>
      )}
    </aside>
  );
}