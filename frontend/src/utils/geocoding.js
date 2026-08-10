const NOMINATIM_BASE_URL = 'https://nominatim.openstreetmap.org';
const MIN_REQUEST_INTERVAL_MS = 1000; // Política de uso: máx. 1 req/seg

let lastRequestTime = 0;
let queue = Promise.resolve();

// Encola las llamadas para respetar el límite de 1 req/seg aunque el
// usuario dibuje varios puntos o busque varias direcciones seguidas.
function throttle(fn) {
  queue = queue.then(async () => {
    const elapsed = Date.now() - lastRequestTime;
    if (elapsed < MIN_REQUEST_INTERVAL_MS) {
      await new Promise((resolve) =>
        setTimeout(resolve, MIN_REQUEST_INTERVAL_MS - elapsed)
      );
    }
    lastRequestTime = Date.now();
    return fn();
  });
  return queue;
}

export async function reverseGeocode(lat, lng) {
  return throttle(async () => {
    const url = `${NOMINATIM_BASE_URL}/reverse?format=jsonv2&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`;

    const response = await fetch(url, {
      headers: { 'Accept-Language': 'es' },
    });

    if (!response.ok) {
      throw new Error(`Nominatim respondió con status ${response.status}`);
    }

    const data = await response.json();

    return {
      displayName: data.display_name ?? null,
      street: data.address?.road ?? null,
      neighbourhood:
        data.address?.neighbourhood ?? data.address?.suburb ?? null,
      city: data.address?.city ?? data.address?.town ?? null,
      raw: data,
    };
  });
}

export async function searchAddress(query) {
  if (!query || query.trim().length < 3) return [];

  return throttle(async () => {
    const params = new URLSearchParams({
      format: 'jsonv2',
      q: query,
      addressdetails: '1',
      limit: '5',
      // Sesga los resultados hacia CDMX sin excluir otras zonas
      viewbox: '-99.4,19.15,-98.9,19.65',
      bounded: '0',
    });

    const response = await fetch(`${NOMINATIM_BASE_URL}/search?${params}`, {
      headers: { 'Accept-Language': 'es' },
    });

    if (!response.ok) {
      throw new Error(`Nominatim respondió con status ${response.status}`);
    }

    const data = await response.json();

    return data.map((item) => ({
      lat: parseFloat(item.lat),
      lng: parseFloat(item.lon),
      displayName: item.display_name,
    }));
  });
}
