import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { MapDataProvider } from './context/MapDataContext';
import MapContainer from './components/map/MapContainer';
import MapDataPanel from './components/MapDataPanel';
import SearchBar from './components/SearchBar';
import Sidebar from './components/sidebar/Sidebar';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return null; // Or a loading spinner
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function PublicRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
}

function AppLayout() {
  const { user } = useAuth();

  return (
    <MapDataProvider>
      <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>
        <Sidebar
          active="mapa"
          onNavigate={(id) => {
            if (id === 'perfil') return; // ajusta cuando exista la página de perfil
            // TODO: navegación real entre secciones (simulaciones, rutas, etc.)
            console.log('nav ->', id);
          }}
          user={{
            name: user?.apodo || user?.nombre || user?.name || 'Invitado',
            role: user?.rol || user?.role || 'Investigador',
          }}
        />
        <div style={{ flex: 1, minWidth: 0, position: 'relative' }}>
          <MapContainer />
          <SearchBar />
          <MapDataPanel />
        </div>
      </div>
    </MapDataProvider>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route
            path="/login"
            element={
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicRoute>
                <RegisterPage />
              </PublicRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;