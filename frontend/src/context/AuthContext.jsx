import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);

const USERS_STORAGE_KEY = 'transystem_users';
const SESSION_STORAGE_KEY = 'transystem_session';

function getStoredUsers() {
  try {
    const data = localStorage.getItem(USERS_STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

function saveUsers(users) {
  localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(users));
}

function getStoredSession() {
  try {
    const data = localStorage.getItem(SESSION_STORAGE_KEY);
    return data ? JSON.parse(data) : null;
  } catch {
    return null;
  }
}

function saveSession(user) {
  if (user) {
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(SESSION_STORAGE_KEY);
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredSession());
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Verify session is still valid on mount
    const session = getStoredSession();
    if (session) {
      const users = getStoredUsers();
      const found = users.find((u) => u.correo === session.correo);
      if (found) {
        setUser(found);
      } else {
        saveSession(null);
        setUser(null);
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback((correo, contrasena) => {
    const users = getStoredUsers();
    const found = users.find((u) => u.correo === correo);

    if (!found) {
      return { success: false, error: 'No se encontró una cuenta con ese correo.' };
    }

    if (found.contrasena !== contrasena) {
      return { success: false, error: 'Contraseña incorrecta.' };
    }

    // Don't expose password to session
    const sessionUser = { ...found };
    delete sessionUser.contrasena;

    setUser(sessionUser);
    saveSession(sessionUser);
    return { success: true };
  }, []);

  const register = useCallback((userData) => {
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

    const users = getStoredUsers();
    const exists = users.find((u) => u.correo === correo);

    if (exists) {
      return { success: false, error: 'Ya existe una cuenta con ese correo.' };
    }

    const newUser = {
      id: crypto.randomUUID(),
      correo,
      contrasena,
      nombre,
      apellido,
      apodo: apodo || '',
      ocupacion: ocupacion || '',
      creadoEn: new Date().toISOString(),
    };

    users.push(newUser);
    saveUsers(users);

    // Auto-login after register
    const sessionUser = { ...newUser };
    delete sessionUser.contrasena;

    setUser(sessionUser);
    saveSession(sessionUser);
    return { success: true };
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    saveSession(null);
  }, []);

  const value = {
    user,
    isLoading,
    isAuthenticated: !!user,
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
