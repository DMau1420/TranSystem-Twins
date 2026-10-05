import React, { createContext, useContext, useState, useCallback, useRef } from 'react';

const MapDataContext = createContext(null);

// Junta coordenadas de formas muy distintas ([lat,lng], {lat,lng}, arreglos
// anidados de un polígono) en una sola lista de pares [lat, lng].
function collectLatLngs(value, out) {
  if (value == null) return;
  if (Array.isArray(value)) {
    if (value.length === 2 && typeof value[0] === 'number' && typeof value[1] === 'number') {
      out.push(value); // ya es [lat, lng]
      return;
    }
    value.forEach((v) => collectLatLngs(v, out));
    return;
  }
  if (typeof value === 'object' && typeof value.lat === 'number' && typeof value.lng === 'number') {
    out.push([value.lat, value.lng]);
  }
}

export const MapDataProvider = ({ children }) => {
  const [points, setPoints] = useState([]);
  const [routes, setRoutes] = useState([]);
  const [zones, setZones] = useState([]);
  const [searchTarget, setSearchTarget] = useState(null);

  // Ids dibujados por Geoman EN ESTA SESIÓN: esas figuras ya están en el mapa
  // (el usuario las ve y puede arrastrarlas), así que MapContainer no las
  // vuelve a dibujar. Lo cargado desde un escenario guardado no tiene raw
  // layer todavía, así que sí se dibuja desde el contexto (ver hydrate).
  const [drawnIds, setDrawnIds] = useState(() => new Set());

  // La capa real de Leaflet detrás de cada id dibujado en vivo. Vive en un
  // ref (no en estado) porque no es serializable y no necesita re-render;
  // solo sirve para poder quitarla del mapa cuando ya no corresponde
  // mostrarla (al borrar un elemento o al cargar otro escenario).
  const drawnLayersRef = useRef(new Map());

  const markDrawn = useCallback((id, layer) => {
    setDrawnIds((prev) => new Set(prev).add(id));
    if (layer) drawnLayersRef.current.set(id, layer);
  }, []);

  const removeDrawnLayer = useCallback((id) => {
    const layer = drawnLayersRef.current.get(id);
    if (layer) {
      try {
        layer.remove();
      } catch {
        /* ya no estaba en el mapa */
      }
      drawnLayersRef.current.delete(id);
    }
  }, []);

  // A dónde debe volar el mapa. Se recalcula en cada hydrate(); MapContainer
  // lo consume y hace flyTo/flyToBounds (mismo patrón que searchTarget).
  const [flyToTarget, setFlyToTarget] = useState(null);

  const addPoint = useCallback((point) => {
    const id = point.id ?? crypto.randomUUID();
    setPoints((prev) => [...prev, { ...point, id }]);
    return id;
  }, []);

  const addRoute = useCallback((route) => {
    const id = route.id ?? crypto.randomUUID();
    setRoutes((prev) => [...prev, { ...route, id }]);
    return id;
  }, []);

  const addZone = useCallback((zone) => {
    const id = zone.id ?? crypto.randomUUID();
    setZones((prev) => [...prev, { vehiculos_por_hora: 0, ...zone, id }]);
    return id;
  }, []);

  const updateZone = useCallback((id, field, value) => {
    setZones((prev) =>
      prev.map((z) => (z.id === id ? { ...z, [field]: value } : z)),
    );
  }, []);

  const removeFeature = useCallback((id) => {
    setPoints((prev) => prev.filter((p) => p.id !== id));
    setRoutes((prev) => prev.filter((r) => r.id !== id));
    setZones((prev) => prev.filter((z) => z.id !== id));
    setDrawnIds((prev) => {
      if (!prev.has(id)) return prev;
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
    removeDrawnLayer(id); // si estaba dibujado en vivo, se quita del mapa
  }, [removeDrawnLayer]);

  // Reemplaza TODO lo marcado por el contenido de un escenario guardado
  // (o lo vacía si se llama sin argumentos): borra del mapa cualquier figura
  // dibujada en vivo en la sesión actual, carga lo nuevo y calcula a dónde volar.
  const hydrate = useCallback((features = {}) => {
    drawnLayersRef.current.forEach((layer) => {
      try {
        layer.remove();
      } catch {
        /* ya no estaba en el mapa */
      }
    });
    drawnLayersRef.current.clear();
    setDrawnIds(new Set());

    const pts = features.points ?? [];
    const rts = features.routes ?? [];
    const zns = features.zones ?? [];

    setPoints(pts);
    setRoutes(rts);
    setZones(zns);

    const latlngs = [];
    pts.forEach((p) => collectLatLngs(p, latlngs));
    rts.forEach((r) => collectLatLngs(r.coordinates, latlngs));
    zns.forEach((z) => collectLatLngs(z.coordinates, latlngs));
    setFlyToTarget(latlngs.length ? { bounds: latlngs } : null);
  }, []);

  const value = {
    points,
    routes,
    zones,
    addPoint,
    addRoute,
    addZone,
    updateZone,
    removeFeature,
    hydrate,
    drawnIds,
    markDrawn,
    flyToTarget,
    searchTarget,
    setSearchTarget,
  };

  return <MapDataContext.Provider value={value}>{children}</MapDataContext.Provider>;
};

export const useMapData = () => {
  const context = useContext(MapDataContext);
  if (!context) {
    throw new Error('useMapData debe usarse dentro de un MapDataProvider');
  }
  return context;
};