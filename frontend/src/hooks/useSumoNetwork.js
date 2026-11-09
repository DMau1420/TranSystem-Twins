import { useEffect, useState } from 'react';
import { cargarRed, convertirRed } from '../utils/sumoNetwork';

// Cache a nivel de módulo: la red pesa ~500 KB y no cambia entre montajes del panel.
let cache = null;

export function useSumoNetwork() {
  const [estado, setEstado] = useState(
    cache ? { red: cache.red, fuente: cache.fuente, cargando: false, error: null } : { red: null, fuente: null, cargando: true, error: null }
  );

  useEffect(() => {
    if (cache) return undefined;
    const ac = new AbortController();
    cargarRed(ac.signal)
      .then(({ geojson, fuente }) => {
        cache = { red: convertirRed(geojson), fuente };
        setEstado({ red: cache.red, fuente, cargando: false, error: null });
      })
      .catch((e) => {
        if (e?.name !== 'AbortError') setEstado({ red: null, fuente: null, cargando: false, error: e });
      });
    return () => ac.abort();
  }, []);

  return estado;
}
