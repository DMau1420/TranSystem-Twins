// src/components/map/SumoNetworkLayer.jsx
import { useEffect, useState } from 'react';
import { GeoJSON } from 'react-leaflet';
import L from 'leaflet';

const SYS_CORE = {
  cian: '#2de3ff',
  magenta: '#ff2d6f',
  ambar: '#ffb020',
};

function estiloFeature(feature) {
  if (feature.geometry.type !== 'LineString') return {};
  const controlada = feature.properties?.controlado_por_semaforo;
  return {
    color: controlada ? SYS_CORE.magenta : SYS_CORE.cian,
    weight: 2,
    opacity: 0.7,
  };
}

function crearIconoSemaforo() {
  return L.divIcon({
    className: 'sumo-semaforo-icon',
    html: `<div style="
      width: 10px; height: 10px; border-radius: 50%;
      background: ${SYS_CORE.ambar};
      box-shadow: 0 0 6px ${SYS_CORE.ambar};
      border: 1px solid #0a0e14;
    "></div>`,
    iconSize: [10, 10],
    iconAnchor: [5, 5],
  });
}

function puntoASemaforo(_feature, latlng) {
  return L.marker(latlng, { icon: crearIconoSemaforo() });
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
  } else if (p.tipo_elemento === 'semaforo') {
    layer.bindPopup(
      `<div class="sys-popup">
        <strong>// SEMAFORO // ${p.tls_id}</strong><br/>
        Tipo: ${p.tipo_control}<br/>
        Entrantes: ${p.calles_entrantes?.length ?? 0}<br/>
        Salientes: ${p.calles_salientes?.length ?? 0}
      </div>`
    );
  }
}

export default function SumoNetworkLayer({ visible = true }) {
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

  return (
    <GeoJSON
      key="sumo-red-network"
      data={red}
      style={estiloFeature}
      pointToLayer={puntoASemaforo}
      onEachFeature={alAdjuntarFeature}
    />
  );
}