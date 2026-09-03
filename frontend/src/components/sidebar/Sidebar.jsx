import { useState } from 'react';
import { useMapTheme } from '../../context/MapThemeContext';
import sunIcon from '../../assets/icons/sun-day.jpg';
import moonIcon from '../../assets/icons/moon-night.jpg';
import './Sidebar.css';

// Iconos inline (sin dependencias externas)
const IconMap = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <path d="M9 4L3 6.5v14L9 18l6 2.5 6-2.5v-14L15 6.5 9 4z" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M9 4v14M15 6.5v14" strokeLinecap="round" />
  </svg>
);
const IconSim = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <path d="M4 18l5-9 4 6 3-4 4 7" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="4" cy="18" r="1.4" />
    <circle cx="20" cy="18" r="1.4" />
  </svg>
);
const IconRoutes = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <circle cx="6" cy="6" r="2.2" />
    <circle cx="18" cy="18" r="2.2" />
    <path d="M6 8.2v3.6a4 4 0 0 0 4 4h4" strokeLinecap="round" />
  </svg>
);
const IconBell = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <path d="M18 16v-5a6 6 0 1 0-12 0v5l-2 3h16l-2-3z" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M10 21a2 2 0 0 0 4 0" strokeLinecap="round" />
  </svg>
);
const IconGear = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 13.5a1.7 1.7 0 0 0 .34 1.87l.06.06a2.06 2.06 0 1 1-2.92 2.92l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1 1.55V20a2.06 2.06 0 1 1-4.12 0v-.09a1.7 1.7 0 0 0-1-1.55 1.7 1.7 0 0 0-1.87.34l-.06.06a2.06 2.06 0 1 1-2.92-2.92l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.55-1H4a2.06 2.06 0 1 1 0-4.12h.09a1.7 1.7 0 0 0 1.55-1 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2.06 2.06 0 1 1 2.92-2.92l.06.06a1.7 1.7 0 0 0 1.87.34H10a1.7 1.7 0 0 0 1-1.55V4a2.06 2.06 0 1 1 4.12 0v.09a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.87-.34l.06-.06a2.06 2.06 0 1 1 2.92 2.92l-.06.06a1.7 1.7 0 0 0-.34 1.87V10a1.7 1.7 0 0 0 1.55 1H20a2.06 2.06 0 1 1 0 4.12h-.09a1.7 1.7 0 0 0-1.55 1z" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const IconUser = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <circle cx="12" cy="8" r="3.4" />
    <path d="M5 20c1.2-4 4-6 7-6s5.8 2 7 6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const IconChevron = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M15 6l-6 6 6 6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const NAV_ITEMS = [
  { id: 'mapa', label: 'Mapa', icon: IconMap, tag: 'NAV_01' },
  { id: 'simulaciones', label: 'Simulaciones', icon: IconSim, tag: 'SIM_ST', badge: 'LIVE', badgeTone: 'cyan' },
  { id: 'rutas', label: 'Rutas', icon: IconRoutes, tag: 'RUT_NET' },
  { id: 'notificaciones', label: 'Notificaciones', icon: IconBell, tag: 'COMM_NET', badge: '04', badgeTone: 'magenta' },
  { id: 'config', label: 'Configuración', icon: IconGear, tag: 'CONF_SYS' },
];

/**
 * Sidebar estilo SYS_CORE (HUD cyberpunk) para TranSystem-Twins.
 * Se coloca al costado del panel de mapa.
 *
 * Props:
 *  - active: id del item activo (default "mapa")
 *  - onNavigate: (id) => void
 *  - user: { name, role, avatarUrl }
 *  - status: { label, value } — franja inferior (ej. conexión MQTT)
 */
export default function Sidebar({
  active = 'mapa',
  onNavigate = () => {},
  user = { name: 'Invitado', role: 'VIEWER' },
  status = { label: 'CONEXIÓN', value: 'MQTT_OK' },
}) {
  const [collapsed, setCollapsed] = useState(false);
  const { mapStyle, toggleMapStyle } = useMapTheme();
  const isDark = mapStyle === 'dark';

  return (
    <aside className={`tst-sidebar ${collapsed ? 'is-collapsed' : 'is-expanded'}`}>
      <div className="tst-sidebar__reticle tst-sidebar__reticle--tl" />
      <div className="tst-sidebar__reticle tst-sidebar__reticle--br" />
      <div className="tst-sidebar__scanline" />

      <header className="tst-sidebar__header">
        <div className="tst-sidebar__brand">
          <span className="tst-sidebar__brand-dot" />
          {!collapsed && (
            <div className="tst-sidebar__brand-text">
              <span className="tst-sidebar__brand-title">TST_CORE</span>
              <span className="tst-sidebar__brand-sub">HOST: NODO_CDMX</span>
            </div>
          )}
        </div>
        <button
          type="button"
          className="tst-sidebar__toggle"
          onClick={() => setCollapsed((c) => !c)}
          aria-label={collapsed ? 'Expandir panel' : 'Colapsar panel'}
        >
          <span className={collapsed ? 'is-flipped' : ''}>
            <IconChevron />
          </span>
        </button>
      </header>

      <nav className="tst-sidebar__nav">
        {NAV_ITEMS.map(({ id, label, icon: Icon, tag, badge, badgeTone }) => {
          const isActive = id === active;
          return (
            <button
              type="button"
              key={id}
              className={`tst-sidebar__item ${isActive ? 'is-active' : ''}`}
              onClick={() => onNavigate(id)}
              title={collapsed ? label : undefined}
            >
              <span className="tst-sidebar__item-icon">
                <Icon />
              </span>
              {!collapsed && (
                <span className="tst-sidebar__item-body">
                  <span className="tst-sidebar__item-tag">{tag}</span>
                  <span className="tst-sidebar__item-label">{label}</span>
                </span>
              )}
              {badge && (
                <span className={`tst-sidebar__badge tst-sidebar__badge--${badgeTone}`}>
                  {badge}
                </span>
              )}
              {isActive && <span className="tst-sidebar__item-indicator" />}
            </button>
          );
        })}
      </nav>

      <div className="tst-sidebar__spacer" />

      {/* Toggle de estilo de mapa: claro/oscuro. Mismo patrón de "switch"
          que ya usa el panel de Capas para Red vial (OSM). */}
      <div className="tst-sidebar__theme-toggle" title="Alternar estilo del mapa">
        <span className={`tst-sidebar__theme-icon-wrap ${!isDark ? 'is-active' : ''}`}>
          <img src={sunIcon} alt="Modo claro" className="tst-sidebar__theme-icon" />
        </span>

        <button
          type="button"
          className={`tst-sidebar__switch ${isDark ? 'is-on' : ''}`}
          onClick={toggleMapStyle}
          aria-pressed={isDark}
          aria-label="Alternar modo oscuro del mapa"
        >
          <span className="tst-sidebar__switch-knob" />
        </button>

        <span className={`tst-sidebar__theme-icon-wrap ${isDark ? 'is-active' : ''}`}>
          <img src={moonIcon} alt="Modo oscuro" className="tst-sidebar__theme-icon" />
        </span>
      </div>

      <button
        type="button"
        className="tst-sidebar__item tst-sidebar__item--profile"
        onClick={() => onNavigate('perfil')}
        title={collapsed ? 'Perfil' : undefined}
      >
        <span className="tst-sidebar__item-icon">
          {user.avatarUrl ? (
            <img src={user.avatarUrl} alt="" className="tst-sidebar__avatar" />
          ) : (
            <IconUser />
          )}
        </span>
        {!collapsed && (
          <span className="tst-sidebar__item-body">
            <span className="tst-sidebar__item-label">{user.name}</span>
            <span className="tst-sidebar__item-tag">{user.role}</span>
          </span>
        )}
      </button>

      <footer className="tst-sidebar__footer">
        {!collapsed ? (
          <>
            <span className="tst-sidebar__footer-dot" />
            <span className="tst-sidebar__footer-text">
              {status.label}: {status.value}
            </span>
          </>
        ) : (
          <span className="tst-sidebar__footer-dot" />
        )}
      </footer>
    </aside>
  );
}