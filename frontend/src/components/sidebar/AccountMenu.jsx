import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext'; // ⚠️ ajustá el path si tu hook vive en otro lado
import './AccountMenu.css';

const DELETE_CONFIRM_WORD = 'ELIMINAR';

/**
 * Menú de cuenta estilo SYS_CORE. Se abre desde el botón de perfil en Sidebar.
 *
 * Rutas usadas (requieren JWT vía Authorization: Bearer <token>):
 *  - GET    /api/me   -> trae { name, email, ... }
 *  - PATCH  /api/me   -> actualiza los campos editables
 *  - DELETE /api/me   -> elimina cuenta + proyectos + escenarios (irreversible)
 *
 * Props:
 *  - isOpen: boolean
 *  - onClose: () => void
 */
export default function AccountMenu({ isOpen, onClose }) {
  const { token, logout } = useAuth();

  const [mode, setMode] = useState('view'); // 'view' | 'edit' | 'delete'
  const [form, setForm] = useState({ name: '', email: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [deleteInput, setDeleteInput] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setMode('view');
    setError(null);
    setDeleteInput('');
    fetchMe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  async function fetchMe() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`GET /api/me -> ${res.status}`);
      const data = await res.json();
      setForm({ name: data.name ?? '', email: data.email ?? '' });
    } catch (err) {
      setError('No se pudo cargar la información de la cuenta.');
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/me', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`PATCH /api/me -> ${res.status}`);
      setMode('view');
    } catch (err) {
      setError('No se pudo guardar los cambios.');
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteAccount() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/me', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`DELETE /api/me -> ${res.status}`);
      logout();
      onClose();
    } catch (err) {
      setError('No se pudo eliminar la cuenta.');
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    logout();
    onClose();
  }

  if (!isOpen) return null;

  return (
    <div className="tst-accmenu__overlay" onClick={onClose}>
      <div
        className="tst-accmenu__panel"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Cuenta de usuario"
      >
        <div className="tst-accmenu__reticle tst-accmenu__reticle--tl" />
        <div className="tst-accmenu__reticle tst-accmenu__reticle--br" />
        <div className="tst-accmenu__scanline" />

        <header className="tst-accmenu__header">
          <span className="tst-accmenu__tag">// ACCOUNT // USER_CTRL</span>
          <button type="button" className="tst-accmenu__close" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </header>

        {error && <div className="tst-accmenu__error">{error}</div>}

        {mode !== 'delete' && (
          <>
            <div className="tst-accmenu__field">
              <label className="tst-accmenu__label">// NOMBRE</label>
              <input
                className="tst-accmenu__input"
                value={form.name}
                disabled={mode !== 'edit' || loading}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>

            <div className="tst-accmenu__field">
              <label className="tst-accmenu__label">// EMAIL</label>
              <input
                className="tst-accmenu__input"
                value={form.email}
                disabled={mode !== 'edit' || loading}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              />
            </div>

            <div className="tst-accmenu__actions">
              {mode === 'view' ? (
                <button
                  type="button"
                  className="tst-accmenu__btn tst-accmenu__btn--cyan"
                  onClick={() => setMode('edit')}
                  disabled={loading}
                >
                  MODIFICAR_DATOS
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    className="tst-accmenu__btn tst-accmenu__btn--cyan"
                    onClick={handleSave}
                    disabled={loading}
                  >
                    GUARDAR
                  </button>
                  <button
                    type="button"
                    className="tst-accmenu__btn tst-accmenu__btn--ghost"
                    onClick={() => {
                      setMode('view');
                      fetchMe();
                    }}
                    disabled={loading}
                  >
                    CANCELAR
                  </button>
                </>
              )}
            </div>

            <div className="tst-accmenu__divider" />

            <button
              type="button"
              className="tst-accmenu__btn tst-accmenu__btn--ghost tst-accmenu__btn--full"
              onClick={handleLogout}
            >
              CERRAR_SESIÓN
            </button>

            <button
              type="button"
              className="tst-accmenu__btn tst-accmenu__btn--danger-outline tst-accmenu__btn--full"
              onClick={() => setMode('delete')}
            >
              ELIMINAR_CUENTA
            </button>
          </>
        )}

        {mode === 'delete' && (
          <div className="tst-accmenu__delete">
            <span className="tst-accmenu__tag tst-accmenu__tag--danger">// WARNING // DATA_LOSS</span>
            <p className="tst-accmenu__warning-text">
              Esta acción es irreversible. Se eliminarán permanentemente tu cuenta,
              todos tus <strong>proyectos</strong> y todos los <strong>escenarios de simulación</strong>{' '}
              asociados. No hay forma de recuperar esta información una vez confirmada.
            </p>

            <label className="tst-accmenu__label">
              Escribe <strong>{DELETE_CONFIRM_WORD}</strong> para confirmar
            </label>
            <input
              className="tst-accmenu__input tst-accmenu__input--danger"
              value={deleteInput}
              onChange={(e) => setDeleteInput(e.target.value)}
              disabled={loading}
              autoComplete="off"
            />

            <div className="tst-accmenu__actions">
              <button
                type="button"
                className="tst-accmenu__btn tst-accmenu__btn--danger"
                disabled={deleteInput !== DELETE_CONFIRM_WORD || loading}
                onClick={handleDeleteAccount}
              >
                CONFIRMAR_ELIMINACIÓN
              </button>
              <button
                type="button"
                className="tst-accmenu__btn tst-accmenu__btn--ghost"
                onClick={() => {
                  setMode('view');
                  setDeleteInput('');
                }}
                disabled={loading}
              >
                CANCELAR
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}