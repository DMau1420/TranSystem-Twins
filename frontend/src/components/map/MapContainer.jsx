import React, { useEffect, useState } from 'react';
import {
  MapContainer as LeafletMap,
  TileLayer,
  ZoomControl,
  useMap,
  Marker,
  Polyline,
  Polygon,
  Tooltip,
} from 'react-leaflet';
import L from 'leaflet';

import 'leaflet/dist/leaflet.css';
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css';
import '@geoman-io/leaflet-geoman-free';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import LayersPanel from './LayersPanel';

import { useMapData } from '../../context/MapDataContext';
import { useMapTheme } from '../../context/MapThemeContext';
import { reverseGeocode } from '../../utils/geocoding';
import { sysCore } from '../../styles/sysCore';
import RoadNetworkLayer from './RoadNetworkLayer';
import SumoNetworkLayer from './SumoNetworkLayer';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const DEFAULT_CENTER = [19.4326, -99.1332];
const DEFAULT_ZOOM = 13;

// Un solo proveedor de tiles (OSM estándar, gratuito, sin API key).
// El "modo oscuro" se logra con un filtro CSS aplicado al TileLayer,
// no con un segundo proveedor — así evitamos depender de servicios
// que exigen registro/API key (ej. CartoDB Dark Matter).
const OSM_TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

const GeomanControls = () => {
  const map = useMap();
  const { addPoint, addRoute, addZone, markDrawn } = useMapData();

  useEffect(() => {
    if (!map || !map.pm) return;

    map.pm.addControls({
      position: 'topleft',
      drawMarker: true,
      drawPolyline: true,
      drawPolygon: true,
      drawCircle: false,
      drawRectangle: false,
      editMode: true,
      dragMode: true,
      removalMode: true,
    });

    const handleCreate = async (e) => {
      const { shape, layer } = e;
      const geoJson = layer.toGeoJSON();

      if (shape === 'Marker') {
        const { lat, lng } = layer.getLatLng();
        let streetInfo = null;
        try {
          streetInfo = await reverseGeocode(lat, lng);
        } catch (err) {
          console.error('Error en reverse geocoding:', err);
        }
        const id = addPoint({
          lat,
          lng,
          geoJson,
          street: streetInfo?.street ?? null,
          displayName: streetInfo?.displayName ?? null,
        });
        markDrawn(id, layer);
      } else if (shape === 'Line') {
        const latlngs = layer.getLatLngs();
        const distanceMeters = latlngs.reduce((total, curr, idx) => {
          if (idx === 0) return 0;
          return total + map.distance(latlngs[idx - 1], curr);
        }, 0);
        const id = addRoute({
          coordinates: latlngs.map((p) => [p.lat, p.lng]),
          geoJson,
          distanceMeters,
        });
        markDrawn(id, layer);
      } else if (shape === 'Polygon') {
        const id = addZone({
          coordinates: layer.getLatLngs(),
          geoJson: geoJson.geometry,
        });
        markDrawn(id, layer);
      }
    };

    map.on('pm:create', handleCreate);

    return () => {
      map.off('pm:create', handleCreate);
      if (map.pm) map.pm.removeControls();
    };
  }, [map, addPoint, addRoute, addZone, markDrawn]);

  return null;
};

// Dibuja lo que llega de un escenario cargado (hydrate). Lo dibujado por
// Geoman en la sesión actual (drawnIds) se deja fuera para no duplicarlo:
// esa figura ya está en el mapa como capa nativa de Geoman, arrastrable.
const FeatureLayers = () => {
  const { points, routes, zones, drawnIds } = useMapData();

  return (
    <>
      {points.filter((p) => !drawnIds.has(p.id)).map((p) => (
        <Marker key={p.id} position={[p.lat, p.lng]} />
      ))}
      {routes.filter((r) => !drawnIds.has(r.id)).map((r) => (
        <Polyline
          key={r.id}
          positions={r.coordinates}
          pathOptions={{ color: sysCore.color.cyan, weight: 4 }}
        />
      ))}
      {zones.filter((z) => !drawnIds.has(z.id)).map((z) => (
        <Polygon
          key={z.id}
          positions={z.coordinates}
          pathOptions={{
            color: sysCore.color.amber,
            fillColor: sysCore.color.amber,
            fillOpacity: 0.15,
            weight: 2,
          }}
        >
          <Tooltip permanent direction="center" className="sys-zone-tooltip">
            {(z.vehiculos_por_hora ?? 0).toLocaleString('es-MX')} veh/h
          </Tooltip>
        </Polygon>
      ))}
    </>
  );
};

const FlyToSearchResult = () => {
  const map = useMap();
  const { searchTarget } = useMapData();

  useEffect(() => {
    if (!map || !searchTarget) return;
    map.flyTo([searchTarget.lat, searchTarget.lng], 17, { duration: 1.2 });
  }, [map, searchTarget]);

  return null;
};

// Vuela a lo que se acaba de cargar (abrir un escenario desde Proyectos).
// flyToTarget se recalcula en cada hydrate(), así que un solo punto usa
// flyTo y varios elementos usan flyToBounds con margen.
const FlyToScenario = () => {
  const map = useMap();
  const { flyToTarget } = useMapData();

  useEffect(() => {
    if (!map || !flyToTarget?.bounds?.length) return;
    const { bounds } = flyToTarget;
    if (bounds.length === 1) {
      map.flyTo(bounds[0], 16, { duration: 1.2 });
    } else {
      map.flyToBounds(bounds, { padding: [60, 60], duration: 1.2 });
    }
  }, [map, flyToTarget]);

  return null;
};

const InvalidateOnResize = () => {
  const map = useMap();

  useEffect(() => {
    if (!map) return;
    const container = map.getContainer();

    map.invalidateSize();

    const observer = new ResizeObserver(() => {
      map.invalidateSize();
    });
    observer.observe(container);

    return () => observer.disconnect();
  }, [map]);

  return null;
};

// Estilo del tooltip de zonas. Va aquí (no en un .css) porque Leaflet genera
// el tooltip fuera del árbol de React normal; ajusta los tokens si cambias
// la paleta SYS_CORE.
const ZONE_TOOLTIP_CSS = `
.sys-zone-tooltip {
  background: rgba(10, 12, 16, 0.9);
  border: 1px solid ${sysCore.color.amber};
  color: ${sysCore.color.amber};
  font-family: ${sysCore.font.mono};
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.03em;
  padding: 2px 6px;
  border-radius: 3px;
  box-shadow: none;
}
.sys-zone-tooltip::before { display: none; }
`;

export const MapContainer = () => {
  const [showRoadNetwork, setShowRoadNetwork] = useState(false);
  const [roadNetworkLoading, setRoadNetworkLoading] = useState(false);
  const [showSumoNetwork, setShowSumoNetwork] = useState(false);
  const { mapStyle } = useMapTheme(); // 'light' | 'dark' — controlado desde el Sidebar

  return (
    <div
      style={{ width: '100%', height: '100%', position: 'relative' }}
      className={mapStyle === 'dark' ? 'sys-map-dark' : undefined}
    >
      <style>{ZONE_TOOLTIP_CSS}</style>
      <LayersPanel
        showRoadNetwork={showRoadNetwork}
        onToggleRoadNetwork={() => setShowRoadNetwork((prev) => !prev)}
        roadNetworkLoading={roadNetworkLoading}
        showSumoNetwork={showSumoNetwork}
        onToggleSumoNetwork={() => setShowSumoNetwork((prev) => !prev)}
      />
      <LeafletMap
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        zoomControl={false}
        style={{ width: '100%', height: '100%' }}
      >
        <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_TILE_URL} maxZoom={19} />
        <ZoomControl position="topright" />
        <GeomanControls />
        <FeatureLayers />
        <FlyToSearchResult />
        <FlyToScenario />
        <InvalidateOnResize />
        <RoadNetworkLayer visible={showRoadNetwork} onLoadingChange={setRoadNetworkLoading} />
        <SumoNetworkLayer visible={showSumoNetwork} />
      </LeafletMap>
    </div>
  );
};

export default MapContainer;