// src/components/map/SumoNetworkLayer.jsx
import { useEffect, useState } from 'react';
import { GeoJSON } from 'react-leaflet';
import L from 'leaflet';

const SYS_CORE = {
  cian: '#2de3ff',
  magenta: '#ff2d6f',
  ambar: '#ffb020',
};

// ⚠️ Id estable de cada calle: el popup nunca mostraba un campo de id, así
// que esto es un supuesto (coincide con "edge_id" del README). Si el campo
// real se llama distinto, ajusta SOLO esta función — todo lo demás ya queda
// enganchado igual.
function edgeIdDe(feature) {
  return feature.properties?.edge_id ?? feature.properties?.id ?? feature.id ?? null;
}

function tlsIdDe(feature) {
  return feature.properties?.tls_id ?? null;
}

function estiloFeature(feature, selectedEdgeId) {
  if (feature.geometry.type !== 'LineString') return {};
  const controlada = feature.properties?.controlado_por_semaforo;
  const selected = edgeIdDe(feature) === selectedEdgeId;

  return {
    color: selected ? SYS_CORE.ambar : controlada ? SYS_CORE.magenta : SYS_CORE.cian,
    weight: selected ? 5 : 2,
    opacity: selected ? 0.95 : 0.7,
  };
}

function crearIconoSemaforo(selected) {
  const size = selected ? 14 : 10;
  return L.divIcon({
    className: 'sumo-semaforo-icon',
    html: `<div style="
      width: ${size}px; height: ${size}px; border-radius: 50%;
      background: ${SYS_CORE.ambar};
      box-shadow: 0 0 ${selected ? 10 : 6}px ${SYS_CORE.ambar};
      border: ${selected ? 2 : 1}px solid #0a0e14;
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

// selectedId: id del edge o tls actualmente seleccionado (o null). Se usa
// solo para resaltar — no filtra ni cambia qué se dibuja.
// onSelectFeature({ kind: 'edge'|'junction', id, baseProps }) se llama al
// hacer clic en una calle o un semáforo.
export default function SumoNetworkLayer({ visible = true, onSelectFeature, selectedId }) {
  const [red, setRed] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!visible || red) return; // ya cargada, no volver a pedir
    const controller = new AbortController();

    fetch('/api/red', { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setRed)
      .catch((err) => {
        if (err.name !== 'AbortError') {
          console.error('[SumoNetworkLayer] Error cargando /api/red:', err);
          setError(err.message);
        }
      });

    return () => controller.abort();
  }, [visible, red]);

  if (!visible || !red) return null;

  function puntoASemaforo(feature, latlng) {
    const selected = tlsIdDe(feature) === selectedId;
    return L.marker(latlng, { icon: crearIconoSemaforo(selected) });
  }

  function alAdjuntarFeature(feature, layer) {
    const p = feature.properties || {};

    if (p.tipo_elemento === 'calle') {
      layer.bindPopup(
        `<div class="sys-popup">
          <strong>// CALLE // ${p.nombre_calle}</strong><br/>
          Carriles: ${p.carriles}<br/>
          Vel. máx: ${p.velocidad_max} km/h<br/>
          Longitud: ${p.longitud} m
          ${p.controlado_por_semaforo ? `<br/>Semáforo: ${p.tls_id}` : ''}
        </div>`
      );
      layer.on('click', () => {
        const id = edgeIdDe(feature);
        if (id != null) onSelectFeature?.({ kind: 'edge', id, baseProps: p });
      });
    } else if (p.tipo_elemento === 'semaforo') {
      layer.bindPopup(
        `<div class="sys-popup">
          <strong>// SEMAFORO // ${p.tls_id}</strong><br/>
          Tipo: ${p.tipo_control}<br/>
          Entrantes: ${p.calles_entrantes?.length ?? 0}<br/>
          Salientes: ${p.calles_salientes?.length ?? 0}
        </div>`
      );
      layer.on('click', () => {
        const id = tlsIdDe(feature);
        if (id != null) onSelectFeature?.({ kind: 'junction', id, baseProps: p });
      });
    }
  }

  return (
    <GeoJSON
      key="sumo-red-network"
      data={red}
      style={(f) => estiloFeature(f, selectedId)}
      pointToLayer={puntoASemaforo}
      onEachFeature={alAdjuntarFeature}
    />
  );
}