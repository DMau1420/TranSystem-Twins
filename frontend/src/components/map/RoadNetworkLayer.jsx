import { useEffect, useRef, useState, useCallback } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import { fetchRoadNetwork } from '../../utils/overpassApi';

const ROAD_STYLE = {
  color: 'var(--sys-cyan, #2de3ff)',
  weight: 1.5,
  opacity: 0.55,
  className: 'sys-road-line',
};

const ROAD_STYLE_MAIN = {
  ...ROAD_STYLE,
  weight: 2.5,
  opacity: 0.75,
};

const MAIN_HIGHWAY_TYPES = new Set(['motorway', 'trunk', 'primary']);

function styleByHighway(feature) {
  const type = feature.properties?.highway;
  return MAIN_HIGHWAY_TYPES.has(type) ? ROAD_STYLE_MAIN : ROAD_STYLE;
}

/**
 * Capa de red vial real (OSM/Overpass) sincronizada con el viewport.
 * @param {{ visible: boolean, onLoadingChange?: (loading: boolean) => void }} props
 */
export default function RoadNetworkLayer({ visible = true, onLoadingChange }) {
  const map = useMap();
  const layerRef = useRef(null);
  const debounceRef = useRef(null);
  const requestIdRef = useRef(0); // identifica la petición "vigente"
  const [error, setError] = useState(null);

  const loadRoads = useCallback(async () => {
    const thisRequestId = ++requestIdRef.current;
    onLoadingChange?.(true);
    setError(null);

    try {
      const bounds = map.getBounds();
      const zoom = map.getZoom();
      const geojson = await fetchRoadNetwork(bounds, zoom);

      // Si mientras esperábamos se disparó otra petición (toggle off/on,
      // o el usuario movió el mapa de nuevo), esta respuesta ya es obsoleta.
      if (thisRequestId !== requestIdRef.current) return;

      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }

      layerRef.current = L.geoJSON(geojson, {
        style: styleByHighway,
        onEachFeature: (feature, layer) => {
          const name = feature.properties?.name;
          if (name) {
            layer.bindTooltip(name, {
              sticky: true,
              className: 'sys-road-tooltip',
            });
          }
        },
      }).addTo(map);
    } catch (err) {
      if (thisRequestId !== requestIdRef.current) return; // también ignoramos errores obsoletos
      console.error('[RoadNetworkLayer] Error cargando red vial:', err);
      setError(err.message);
    } finally {
      if (thisRequestId === requestIdRef.current) {
        onLoadingChange?.(false);
      }
    }
  }, [map, onLoadingChange]);

  useEffect(() => {
    if (!visible) {
      requestIdRef.current++; // invalida cualquier petición en vuelo
      onLoadingChange?.(false);
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
      return;
    }

    loadRoads(); // carga inicial / al activar

    const handleMoveEnd = () => {
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(loadRoads, 500);
    };

    map.on('moveend', handleMoveEnd);
    return () => {
      map.off('moveend', handleMoveEnd);
      clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, loadRoads, map]);

  return null;
}