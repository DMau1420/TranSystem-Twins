import React, { useEffect, useState } from 'react';
import { MapContainer as LeafletMap, TileLayer, ZoomControl, useMap } from 'react-leaflet';
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
import RoadNetworkLayer from './RoadNetworkLayer';

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
  const { addPoint, addRoute, addZone } = useMapData();

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
        addPoint({
          lat,
          lng,
          geoJson,
          street: streetInfo?.street ?? null,
          displayName: streetInfo?.displayName ?? null,
        });
      } else if (shape === 'Line') {
        const latlngs = layer.getLatLngs();
        const distanceMeters = latlngs.reduce((total, curr, idx) => {
          if (idx === 0) return 0;
          return total + map.distance(latlngs[idx - 1], curr);
        }, 0);
        addRoute({
          coordinates: latlngs.map((p) => [p.lat, p.lng]),
          geoJson,
          distanceMeters,
        });
      } else if (shape === 'Polygon') {
        addZone({
          coordinates: layer.getLatLngs(),
          geoJson: geoJson.geometry,
        });
      }
    };

    map.on('pm:create', handleCreate);

    return () => {
      map.off('pm:create', handleCreate);
      if (map.pm) map.pm.removeControls();
    };
  }, [map, addPoint, addRoute, addZone]);

  return null;
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

export const MapContainer = () => {
  const [showRoadNetwork, setShowRoadNetwork] = useState(false);
  const [roadNetworkLoading, setRoadNetworkLoading] = useState(false);
  const { mapStyle } = useMapTheme(); // 'light' | 'dark' — controlado desde el Sidebar

  return (
    <div
      style={{ width: '100%', height: '100%', position: 'relative' }}
      className={mapStyle === 'dark' ? 'sys-map-dark' : undefined}
    >
      <LayersPanel
        showRoadNetwork={showRoadNetwork}
        onToggleRoadNetwork={() => setShowRoadNetwork((prev) => !prev)}
        roadNetworkLoading={roadNetworkLoading}
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
        <FlyToSearchResult />
        <InvalidateOnResize />
        <RoadNetworkLayer visible={showRoadNetwork} onLoadingChange={setRoadNetworkLoading} />
      </LeafletMap>
    </div>
  );
};

export default MapContainer;