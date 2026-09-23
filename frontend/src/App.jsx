function AppLayout() {
  const { user } = useAuth();

  return (
    <MapThemeProvider>
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
              name: user?.apodo || user?.nombre || user?.name || user?.username || 'Invitado',
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
    </MapThemeProvider>
  );
}