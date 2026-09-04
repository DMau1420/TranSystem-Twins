import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { loginApi, registerApi } from '../api/authApi';

const AuthContext = createContext(null);

const TOKEN_STORAGE_KEY = 'transystem_token';
const USER_STORAGE_KEY = 'transystem_user';

function decodeJwtPayload(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

function getStoredUser() {
  try {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    const userData = localStorage.getItem(USER_STORAGE_KEY);
    if (!token || !userData) return null;

    const payload = decodeJwtPayload(token);
    if (payload?.exp && payload.exp * 1000 < Date.now()) {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(USER_STORAGE_KEY);
      return null;
    }

    return JSON.parse(userData);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredUser());
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = getStoredUser();
    setUser(stored);
    setIsLoading(false);
  }, []);

  const login = useCallback(async (correo, contrasena) => {
    try {
      const data = await loginApi({ correo, password: contrasena });
      const payload = decodeJwtPayload(data.access_token);

      const sessionUser = {
        id: payload?.sub || crypto.randomUUID(),
        correo: payload?.correo || correo,
        nombre: payload?.nombre || correo.split('@')[0],
        apodo: payload?.apodo || null,
        rol: payload?.rol || 'Investigador',
        token: data.access_token,
      };

      localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(sessionUser));

      setUser(sessionUser);
      return { success: true };
    } catch (err) {
      return {
        success: false,
        error: err.message || 'Credenciales incorrectas o problema de conexión con el servidor.',
      };
    }
  }, []);

  const register = useCallback(
    async (userData) => {
      const { correo, contrasena, nombre, apellido, apodo, ocupacion } = userData;

      if (!correo || !contrasena || !nombre || !apellido) {
        return { success: false, error: 'Completa todos los campos obligatorios.' };
      }

      if (contrasena.length < 6) {
        return { success: false, error: 'La contraseña debe tener al menos 6 caracteres.' };
      }

      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(correo)) {
        return { success: false, error: 'Ingresa un correo electrónico válido.' };
      }

      try {
        const fullName = `${nombre.trim()} ${apellido.trim()}`;
        const registeredUser = await registerApi({
          nombre: fullName,
          apodo: apodo?.trim() || null,
          correo: correo.trim(),
          password: contrasena,
          rol: ocupacion || 'Investigador',
        });

        // Iniciar sesión automáticamente tras el registro exitoso
        const loginResult = await login(correo.trim(), contrasena);

        if (loginResult.success) {
          setUser((prev) => {
            const updated = {
              ...prev,
              nombre: registeredUser.nombre || fullName,
              apodo: registeredUser.apodo || apodo?.trim() || null,
              rol: registeredUser.rol || prev?.rol || 'Investigador',
            };
            localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(updated));
            return updated;
          });
        }

        return { success: true };
      } catch (err) {
        return {
          success: false,
          error: err.message || 'Error al registrar la cuenta en el servidor.',
        };
      }
    },
    [login]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
    setUser(null);
  }, []);

  const value = {
    user,
    isLoading,
    isAuthenticated: !!user,
    token: localStorage.getItem(TOKEN_STORAGE_KEY),
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth debe usarse dentro de un AuthProvider');
  }
  return context;
}

export default AuthContext;
