import React, { createContext, useState, useEffect } from "react";
import { AuthAPI } from "../services/api";

interface AuthContextType {
  user: any;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  loginWithGitHub: () => void;
  loginWithGoogle: () => void;
  handleOAuthCallback: (token: string, user: any) => void;
  updateUserProfile: (profileData: { name?: string }) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  login: async () => {},
  register: async () => {},
  loginWithGitHub: () => {},
  loginWithGoogle: () => {},
  handleOAuthCallback: () => {},
  updateUserProfile: async () => {},
  logout: () => {}
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<any>(null);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    // Load from localStorage on mount
    const storedToken = localStorage.getItem("token");
    const storedUser = localStorage.getItem("user");
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      // Set the token in the API service so it can make authenticated requests
      AuthAPI.setToken(storedToken);
    }
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await AuthAPI.login(email, password);
      if (response.success && response.data) {
        setToken(response.data.token);
        setUser(response.data.user);
        localStorage.setItem("token", response.data.token);
        localStorage.setItem("user", JSON.stringify(response.data.user));
        // Update API service with the new token
        AuthAPI.setToken(response.data.token);
      } else {
        throw new Error(response.error?.message || "Login failed");
      }
    } catch (error: any) {
      throw new Error(error.message || "Login failed");
    }
  };

  const register = async (email: string, password: string, name: string) => {
    try {
      const response = await AuthAPI.register(email, password, name);
      if (response.success && response.data) {
        setToken(response.data.token);
        setUser(response.data.user);
        localStorage.setItem("token", response.data.token);
        localStorage.setItem("user", JSON.stringify(response.data.user));
        // Update API service with the new token
        AuthAPI.setToken(response.data.token);
      } else {
        throw new Error(response.error?.message || "Registration failed");
      }
    } catch (error: any) {
      throw new Error(error.message || "Registration failed");
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    // Clear token from API service
    AuthAPI.setToken(null);
  };

  const loginWithGitHub = () => {
    const baseUrl = (import.meta as any).env?.VITE_GAMEFORGE_API_URL || "http://localhost:8080";
    window.location.href = `${baseUrl}/api/v1/auth/github`;
  };

  const loginWithGoogle = () => {
    const baseUrl = (import.meta as any).env?.VITE_GAMEFORGE_API_URL || "http://localhost:8080";
    window.location.href = `${baseUrl}/api/v1/auth/google`;
  };

  const handleOAuthCallback = (token: string, user: any) => {
    setToken(token);
    setUser(user);
    localStorage.setItem("token", token);
    localStorage.setItem("user", JSON.stringify(user));
    // Update API service with the new token
    AuthAPI.setToken(token);
  };

  const updateUserProfile = async (profileData: { name?: string }) => {
    try {
      const response = await AuthAPI.updateProfile(profileData);
      if (response.success && response.data) {
        // Update the user state with the new data
        const updatedUser = response.data.user;
        setUser(updatedUser);
        localStorage.setItem("user", JSON.stringify(updatedUser));
        
        // Update token if a new one was provided
        if (response.data.access_token) {
          setToken(response.data.access_token);
          localStorage.setItem("token", response.data.access_token);
        }
      } else {
        throw new Error(response.error?.message || "Profile update failed");
      }
    } catch (error: any) {
      throw new Error(error.message || "Profile update failed");
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, loginWithGitHub, loginWithGoogle, handleOAuthCallback, updateUserProfile, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
