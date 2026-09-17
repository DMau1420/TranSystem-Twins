import osmtogeojson from 'osmtogeojson';

const OVERPASS_ENDPOINTS = [
  'https://overpass.kumi.systems/api/interpreter',
  'https://overpass.private.coffee/api/interpreter',
  'https://overpass-api.de/api/interpreter',
];

const OVERPASS_URL = 'https://overpass-api.de/api/interpreter';
const MIN_REQUEST_INTERVAL = 1000;
const MIN_ZOOM_FOR_FETCH = 14;
const REQUEST_TIMEOUT_MS = 15000; // si Overpass no responde en 15s, abortamos

let lastRequestTime = 0;
let currentController = null; // permite cancelar la petición en vuelo
const bboxCache = new Map();

function roundBbox(bbox, precision = 3) {
  return bbox.map((n) => n.toFixed(precision)).join(',');
}

async function throttle() {
  const elapsed = Date.now() - lastRequestTime;
  if (elapsed < MIN_REQUEST_INTERVAL) {
    await new Promise((res) => setTimeout(res, MIN_REQUEST_INTERVAL - elapsed));
  }
  lastRequestTime = Date.now();
}

const HIGHWAY_TAGS = [
  'motorway',
  'trunk',
  'primary',
  'secondary',
  'tertiary',
  'unclassified',
  'residential',
  'motorway_link',
  'trunk_link',
  'primary_link',
  'secondary_link',
  'tertiary_link',
];

function buildQuery(south, west, north, east) {
  const tagFilter = HIGHWAY_TAGS.map(
    (t) => `way["highway"="${t}"](${south},${west},${north},${east});`
  ).join('\n      ');
  return `
    [out:json][timeout:25];
    (
      ${tagFilter}
    );
    out geom;
  `;
}

export async function fetchRoadNetwork(bounds, zoom) {
  if (zoom < MIN_ZOOM_FOR_FETCH) {
    return { type: 'FeatureCollection', features: [], skipped: 'zoom_too_low' };
  }

  const south = bounds.getSouth();
  const west = bounds.getWest();
  const north = bounds.getNorth();
  const east = bounds.getEast();

  const cacheKey = roundBbox([south, west, north, east]);
  if (bboxCache.has(cacheKey)) {
    return bboxCache.get(cacheKey);
  }

  // Si había una petición anterior en vuelo, la cancelamos —
  // ya no nos interesa su resultado y así liberamos al servidor.
  if (currentController) {
    currentController.abort();
  }
  currentController = new AbortController();
  const { signal } = currentController;

  await throttle();

  const query = buildQuery(south, west, north, east);

  const timeoutId = setTimeout(
    () => currentController?.abort(),
    REQUEST_TIMEOUT_MS
  );

  try {
    const response = await fetch(OVERPASS_URL, {
      method: 'POST',
      body: `data=${encodeURIComponent(query)}`,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      signal,
    });

    if (!response.ok) {
      throw new Error(`Overpass error: ${response.status}`);
    }

    const osmData = await response.json();
    const geojson = osmtogeojson(osmData);

    bboxCache.set(cacheKey, geojson);
    return geojson;
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error(
        'Overpass no respondió a tiempo (timeout o petición cancelada)'
      );
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export function clearRoadNetworkCache() {
  bboxCache.clear();
}
