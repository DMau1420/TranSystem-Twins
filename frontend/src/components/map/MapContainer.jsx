import React, { useEffect } from 'react';
import { MapContainer as LeafletMap, TileLayer, ZoomControl, useMap } from 'react-leaflet';
import L from 'leaflet';

import 'leaflet/dist/leaflet.css';
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css';
import '@geoman-io/leaflet-geoman-free';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const DEFAULT_CENTER = [19.4326, -99.1332];
const DEFAULT_ZOOM = 13;

const GeomanControls = () => {
  const map = useMap();

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

    map.on('pm:create', (e) => {
      const { shape, layer } = e;
      const geoJsonData = layer.toGeoJSON();
      console.log(`Infraestructura agregada (${shape}):`, geoJsonData);
    });

    return () => {
      if (map.pm) {
        map.pm.removeControls();
      }
    };
  }, [map]);

  return null;
};

export const MapContainer = () => {
  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      <LeafletMap
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        zoomControl={false}
        style={{ width: '100%', height: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        <ZoomControl position="topright" />
        <GeomanControls />
      </LeafletMap>
    </div>
  );
};

export default MapContainer;