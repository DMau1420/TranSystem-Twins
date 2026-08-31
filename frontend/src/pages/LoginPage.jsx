import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Auth.css';

function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [correo, setCorreo] = useState('');
  const [contrasena, setContrasena] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!correo || !contrasena) {
      setError('Completa todos los campos.');
      return;
    }

    setIsLoading(true);

    // Simulate brief network delay for UX
    await new Promise((r) => setTimeout(r, 600));

    const result = login(correo, contrasena);

    if (!result.success) {
      setError(result.error);
      setIsLoading(false);
      return;
    }

    setShowSuccess(true);
    setTimeout(() => navigate('/'), 1000);
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
          <span>STATE: LOGIN // SECURE</span>
          <span className="auth-dot-group">
            <span className="auth-pulse-dot" />
            ONLINE
          </span>
        </div>

        <div className="auth-brand">
          <div className="auth-brand-icon">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
          </div>
          <span className="auth-eyebrow">AUTH_MODULE // SIG_IN</span>
          <h1>Bienvenido de vuelta</h1>
          <p>Inicia sesión en TranSystem Twins</p>
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

          <div className="auth-field">
            <label htmlFor="login-email">Correo electrónico</label>
            <input
              id="login-email"
              type="email"
              placeholder="tu@correo.com"
              value={correo}
              onChange={(e) => setCorreo(e.target.value)}
              autoComplete="email"
              autoFocus
            />
          </div>

          <div className="auth-field">
            <label htmlFor="login-password">Contraseña</label>
            <div className="auth-password-wrapper">
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={contrasena}
                onChange={(e) => setContrasena(e.target.value)}
                autoComplete="current-password"
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

          <button
            type="submit"
            className="auth-submit"
            disabled={isLoading}
          >
            {isLoading ? <span className="auth-spinner" /> : <span>Iniciar Sesión</span>}
          </button>
        </form>

        <div className="auth-footer">
          <span>¿No tienes cuenta?</span>
          <Link to="/register">Crear cuenta</Link>
        </div>

        <div className="auth-metabar">
          <span><span className="auth-metabar-chip chip-cyan" />ENCRYPTION: AES_256</span>
          <span><span className="auth-metabar-chip chip-magenta" />STATUS: STABLE</span>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;