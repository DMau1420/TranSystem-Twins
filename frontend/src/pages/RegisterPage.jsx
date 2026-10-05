import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Auth.css';

function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    correo: '',
    contrasena: '',
    confirmarContrasena: '',
    nombre: '',
    apellido: '',
    apodo: '',
    ocupacion: '',
  });

  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const updateField = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!form.nombre || !form.apellido || !form.correo || !form.contrasena) {
      setError('Completa todos los campos obligatorios.');
      return;
    }

    if (form.contrasena !== form.confirmarContrasena) {
      setError('Las contraseñas no coinciden.');
      return;
    }

    if (form.contrasena.length < 6) {
      setError('La contraseña debe tener al menos 6 caracteres.');
      return;
    }

    setIsLoading(true);

    const result = await register({
      correo: form.correo,
      contrasena: form.contrasena,
      nombre: form.nombre,
      apellido: form.apellido,
      apodo: form.apodo,
      ocupacion: form.ocupacion,
    });

    if (!result.success) {
      setError(result.error);
      setIsLoading(false);
      return;
    }

    setShowSuccess(true);
    setTimeout(() => navigate('/'), 800);
  };

  return (
    <div className="auth-page">
      {showSuccess && (
        <div className="auth-success-overlay">
          <div className="auth-success-check">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
        </div>
      )}

      <div className="auth-card">
        <span className="auth-corner-tl" />
        <span className="auth-corner-tr" />
        <span className="auth-corner-bl" />
        <span className="auth-corner-br" />

        <div className="auth-statusline">
          <span>STATE: REGISTER // NEW_NODE</span>
          <span className="auth-dot-group">
            <span className="auth-pulse-dot" />
            ONLINE
          </span>
        </div>

        <div className="auth-brand">
          <div className="auth-brand-icon">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4-4v-2" />
              <circle cx="8.5" cy="7" r="4" />
              <line x1="20" y1="8" x2="20" y2="14" />
              <line x1="23" y1="11" x2="17" y2="11" />
            </svg>
          </div>
          <span className="auth-eyebrow">AUTH_MODULE // SIG_UP</span>
          <h1>Crear cuenta</h1>
          <p>Regístrate en TranSystem Twins</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {error && (
            <div className="auth-error">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {/* Nombre y Apellido */}
          <div className="auth-field-row">
            <div className="auth-field">
              <label htmlFor="reg-nombre">Nombre</label>
              <input
                id="reg-nombre"
                type="text"
                placeholder="Juan"
                value={form.nombre}
                onChange={updateField('nombre')}
                autoFocus
              />
            </div>
            <div className="auth-field">
              <label htmlFor="reg-apellido">Apellido</label>
              <input
                id="reg-apellido"
                type="text"
                placeholder="Pérez"
                value={form.apellido}
                onChange={updateField('apellido')}
              />
            </div>
          </div>

          {/* Correo */}
          <div className="auth-field">
            <label htmlFor="reg-email">Correo electrónico</label>
            <input
              id="reg-email"
              type="email"
              placeholder="tu@correo.com"
              value={form.correo}
              onChange={updateField('correo')}
              autoComplete="email"
            />
          </div>

          {/* Contraseña */}
          <div className="auth-field">
            <label htmlFor="reg-password">Contraseña</label>
            <div className="auth-password-wrapper">
              <input
                id="reg-password"
                type={showPassword ? 'text' : 'password'}
                placeholder="Mínimo 6 caracteres"
                value={form.contrasena}
                onChange={updateField('contrasena')}
                autoComplete="new-password"
              />
              <button
                type="button"
                className="auth-password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
              >
                {showPassword ? (
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Confirmar Contraseña */}
          <div className="auth-field">
            <label htmlFor="reg-confirm-password">Confirmar contraseña</label>
            <input
              id="reg-confirm-password"
              type={showPassword ? 'text' : 'password'}
              placeholder="Repite tu contraseña"
              value={form.confirmarContrasena}
              onChange={updateField('confirmarContrasena')}
              autoComplete="new-password"
            />
          </div>

          {/* Apodo y Ocupación — opcionales */}
          <div className="auth-field-row">
            <div className="auth-field">
              <label htmlFor="reg-apodo">
                Apodo <span className="auth-optional">(opcional)</span>
              </label>
              <input
                id="reg-apodo"
                type="text"
                placeholder="Tu apodo"
                value={form.apodo}
                onChange={updateField('apodo')}
              />
            </div>
            <div className="auth-field">
              <label htmlFor="reg-ocupacion">
                Ocupación <span className="auth-optional">(opcional)</span>
              </label>
              <input
                id="reg-ocupacion"
                type="text"
                placeholder="Ej: Ingeniero"
                value={form.ocupacion}
                onChange={updateField('ocupacion')}
              />
            </div>
          </div>

          <button
            type="submit"
            className="auth-submit"
            disabled={isLoading}
          >
            {isLoading ? <span className="auth-spinner" /> : <span>Crear Cuenta</span>}
          </button>
        </form>

        <div className="auth-footer">
          <span>¿Ya tienes cuenta?</span>
          <Link to="/login">Iniciar sesión</Link>
        </div>

        <div className="auth-metabar">
          <span><span className="auth-metabar-chip chip-cyan" />ENCRYPTION: AES_256</span>
          <span><span className="auth-metabar-chip chip-magenta" />NODE: NEW_USER</span>
        </div>
      </div>
    </div>
  );
}

export default RegisterPage;