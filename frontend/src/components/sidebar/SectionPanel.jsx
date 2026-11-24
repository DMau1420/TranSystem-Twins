import { useEffect } from 'react';
import '../dashboard/ProjectsPanel.css';

/**
 * Marco de panel lateral para las pestañas del Sidebar.
 * Reutiliza las clases tst-projects__* de ProjectsPanel para que se vea igual
 * y se comporte igual (panel de flujo normal: empuja el mapa a la derecha).
 *
 * Props:
 *  - tag:      texto pequeño superior, p. ej. "// SIM_ST // SIMULACIONES"
 *  - title:    título del panel
 *  - onClose:  () => void
 *  - children: contenido
 */
export default function SectionPanel({ tag, title, onClose, children }) {
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <aside className="tst-projects__panel" aria-label={title}>
      <div className="tst-projects__reticle tst-projects__reticle--tl" />
      <div className="tst-projects__reticle tst-projects__reticle--br" />
      <div className="tst-projects__scanline" />

      <header className="tst-projects__header">
        <div className="tst-projects__header-left">
          <div className="tst-projects__header-text">
            <span className="tst-projects__tag">{tag}</span>
            <span className="tst-projects__title">{title}</span>
          </div>
        </div>
        <div className="tst-projects__header-right">
          <button
            type="button"
            className="tst-projects__close"
            onClick={onClose}
            aria-label="Cerrar panel"
          >
            ×
          </button>
        </div>
      </header>

      <div className="tst-projects__body">{children}</div>
    </aside>
  );
}