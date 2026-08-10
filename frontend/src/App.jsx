import { MapDataProvider } from './context/MapDataContext';
import MapContainer from './components/map/MapContainer';
import MapDataPanel from './components/MapDataPanel';
import SearchBar from './components/SearchBar';

function App() {
  return (
    <MapDataProvider>
      <MapContainer />
      <SearchBar />
      <MapDataPanel />
    </MapDataProvider>
  );
}

export default App;