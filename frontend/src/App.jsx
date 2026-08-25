import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { MapDataProvider } from './context/MapDataContext';
import MapContainer from './components/map/MapContainer';
import MapDataPanel from './components/MapDataPanel';
import SearchBar from './components/SearchBar';
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
  return (
    <MapDataProvider>
      <MapContainer />
      <SearchBar />
      <MapDataPanel />
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