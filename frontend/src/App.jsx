import React from 'react';
import MapContainer from './components/map/MapContainer';

function App() {
  return (
    <main style={{ width: '100vw', height: '100vh', margin: 0, padding: 0 }}>
      {/* Contenedor principal del Mapa Interactivo y Editor de Escenarios */}
      <MapContainer />
    </main>
  );
}

export default App;