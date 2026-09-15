import React, { createContext, useContext, useState, useCallback } from 'react';

const MapDataContext = createContext(null);

export const MapDataProvider = ({ children }) => {
  const [points, setPoints] = useState([]);
  const [routes, setRoutes] = useState([]);
  const [zones, setZones] = useState([]);
  const [searchTarget, setSearchTarget] = useState(null);

  const addPoint = useCallback((point) => {
    setPoints((prev) => [...prev, { id: crypto.randomUUID(), ...point }]);
  }, []);

  const addRoute = useCallback((route) => {
    setRoutes((prev) => [...prev, { id: crypto.randomUUID(), ...route }]);
  }, []);

  const addZone = useCallback((zone) => {
    setZones((prev) => [...prev, { id: crypto.randomUUID(), vehiculos_por_hora: 0, ...zone }]);
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