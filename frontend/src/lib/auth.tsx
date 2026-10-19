import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from './api';
import { User } from './types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; target_role?: string; daily_study_minutes?: number }) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('skillissue_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    try {
      if (token) {
        const userData = await api.get<User>('/auth/me');
        setUser(userData);
        localStorage.setItem('skillissue_user', JSON.stringify(userData));
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
      setToken(null);
      localStorage.removeItem('skillissue_token');
      localStorage.removeItem('skillissue_user');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, [token]);

  const login = async (email: string, password: string) => {
    const res = await api.post<{ access_token: string; user_id: string; email: string }>('/auth/login', {
      email,
      password,
    });
    localStorage.setItem('skillissue_token', res.access_token);
    setToken(res.access_token);
    await refreshUser();
  };

  const register = async (data: { email: string; password: string; target_role?: string; daily_study_minutes?: number }) => {
    await api.post('/auth/register', data);
    await login(data.email, data.password);
  };

  const logout = () => {
    localStorage.removeItem('skillissue_token');
    localStorage.removeItem('skillissue_user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
