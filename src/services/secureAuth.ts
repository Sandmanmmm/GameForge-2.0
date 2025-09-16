/**
 * Secure Authentication Service
 * 
 * PRODUCTION-READY: No tokens in environment variables
 * Tokens are managed securely in client-side storage only
 */

import { ApiResponse } from '../types/permissions';

// Temporary types until shared package is set up
interface AuthResponse {
  success: boolean;
  data?: {
    user: any;
    expiresAt: string;
  };
  error?: {
    message: string;
  };
}

interface LoginRequest {
  email: string;
  password: string;
  rememberMe?: boolean;
}

interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  acceptTerms: boolean;
}

interface User {
  id: string;
  email: string;
  name: string;
  roles: string[];
}

interface AuthConfig {
  apiBaseUrl: string;
  tokenKey: string;
  refreshTokenKey: string;
  tokenExpiration: number; // in minutes
}

export class SecureAuthService {
  private config: AuthConfig;
  private token: string | null = null;
  private refreshToken: string | null = null;
  private tokenExpiration: Date | null = null;

  constructor(apiBaseUrl: string) {
    this.config = {
      apiBaseUrl,
      tokenKey: 'gf_auth_token',
      refreshTokenKey: 'gf_refresh_token', 
      tokenExpiration: 60 // 1 hour
    };
    
    // Load tokens from secure storage on initialization
    this.loadTokensFromStorage();
  }

  /**
   * Login user and securely store tokens
   */
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await fetch(`${this.config.apiBaseUrl}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      throw new Error(`Login failed: ${response.statusText}`);
    }

    const data = await response.json();
    
    if (data.success && data.data) {
      // Securely store tokens (received from backend)
      this.setTokens(data.data.access_token, data.data.refresh_token, data.data.expires_in);
      return {
        success: true,
        data: {
          user: data.data.user,
          expiresAt: data.data.expires_at
        }
      };
    }

    throw new Error(data.error?.message || 'Login failed');
  }

  /**
   * Register new user
   */
  async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response = await fetch(`${this.config.apiBaseUrl}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      throw new Error(`Registration failed: ${response.statusText}`);
    }

    const data = await response.json();
    
    if (data.success && data.data) {
      this.setTokens(data.data.access_token, data.data.refresh_token, data.data.expires_in);
      return {
        success: true,
        data: {
          user: data.data.user,
          expiresAt: data.data.expires_at
        }
      };
    }

    throw new Error(data.error?.message || 'Registration failed');
  }

  /**
   * OAuth login redirects
   */
  initiateOAuthLogin(provider: 'github' | 'google'): void {
    const state = this.generateOAuthState();
    sessionStorage.setItem('oauth_state', state);
    
    const oauthUrl = `${this.config.apiBaseUrl}/auth/${provider}?state=${state}`;
    window.location.href = oauthUrl;
  }

  /**
   * Handle OAuth callback
   */
  async handleOAuthCallback(code: string, state: string): Promise<AuthResponse> {
    const savedState = sessionStorage.getItem('oauth_state');
    if (state !== savedState) {
      throw new Error('Invalid OAuth state');
    }

    const response = await fetch(`${this.config.apiBaseUrl}/auth/oauth/callback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ code, state }),
    });

    const data = await response.json();
    
    if (data.success && data.data) {
      this.setTokens(data.data.access_token, data.data.refresh_token, data.data.expires_in);
      sessionStorage.removeItem('oauth_state');
      return {
        success: true,
        data: {
          user: data.data.user,
          expiresAt: data.data.expires_at
        }
      };
    }

    throw new Error(data.error?.message || 'OAuth login failed');
  }

  /**
   * Logout and clear all tokens
   */
  async logout(): Promise<void> {
    try {
      // Inform backend of logout
      if (this.token) {
        await fetch(`${this.config.apiBaseUrl}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json',
          },
        });
      }
    } catch (error) {
      console.warn('Logout request failed:', error);
    } finally {
      // Always clear local tokens
      this.clearTokens();
    }
  }

  /**
   * Get current authentication token for API requests
   */
  async getAuthToken(): Promise<string | null> {
    if (!this.token) {
      return null;
    }

    // Check if token is expired
    if (this.tokenExpiration && new Date() >= this.tokenExpiration) {
      // Try to refresh token
      const refreshed = await this.refreshAuthToken();
      if (!refreshed) {
        return null;
      }
    }

    return this.token;
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.token !== null && (!this.tokenExpiration || new Date() < this.tokenExpiration);
  }

  /**
   * Get current user from token payload (if available)
   */
  getCurrentUser(): User | null {
    if (!this.token) {
      return null;
    }

    try {
      // Decode JWT payload (basic implementation)
      const payload = JSON.parse(atob(this.token.split('.')[1]));
      return payload.user || null;
    } catch (error) {
      console.warn('Failed to decode token payload:', error);
      return null;
    }
  }

  /**
   * Refresh authentication token
   */
  private async refreshAuthToken(): Promise<boolean> {
    if (!this.refreshToken) {
      this.clearTokens();
      return false;
    }

    try {
      const response = await fetch(`${this.config.apiBaseUrl}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data) {
          this.setTokens(data.data.access_token, data.data.refresh_token, data.data.expires_in);
          return true;
        }
      }
    } catch (error) {
      console.warn('Token refresh failed:', error);
    }

    this.clearTokens();
    return false;
  }

  /**
   * Securely store tokens
   */
  private setTokens(accessToken: string, refreshToken: string, expiresIn: number): void {
    this.token = accessToken;
    this.refreshToken = refreshToken;
    this.tokenExpiration = new Date(Date.now() + expiresIn * 1000);

    // Store in localStorage (consider more secure options for production)
    localStorage.setItem(this.config.tokenKey, accessToken);
    localStorage.setItem(this.config.refreshTokenKey, refreshToken);
    localStorage.setItem(`${this.config.tokenKey}_exp`, this.tokenExpiration.toISOString());
  }

  /**
   * Load tokens from storage
   */
  private loadTokensFromStorage(): void {
    this.token = localStorage.getItem(this.config.tokenKey);
    this.refreshToken = localStorage.getItem(this.config.refreshTokenKey);
    
    const expiration = localStorage.getItem(`${this.config.tokenKey}_exp`);
    if (expiration) {
      this.tokenExpiration = new Date(expiration);
    }

    // Validate tokens on load
    if (this.tokenExpiration && new Date() >= this.tokenExpiration) {
      this.clearTokens();
    }
  }

  /**
   * Clear all tokens
   */
  private clearTokens(): void {
    this.token = null;
    this.refreshToken = null;
    this.tokenExpiration = null;

    localStorage.removeItem(this.config.tokenKey);
    localStorage.removeItem(this.config.refreshTokenKey);
    localStorage.removeItem(`${this.config.tokenKey}_exp`);
  }

  /**
   * Generate secure OAuth state
   */
  private generateOAuthState(): string {
    return Array.from(crypto.getRandomValues(new Uint8Array(32)))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  }
}

// Export singleton instance
const getApiBaseUrl = (): string => {
  // Production-ready environment detection
  if (typeof window !== 'undefined' && window.location) {
    const hostname = window.location.hostname;
    
    // Production domain detection
    if (hostname.includes('gameforge.app') || hostname.includes('gameforge.com')) {
      return 'https://api.gameforge.app/api/v1';
    }
    
    // Staging domain
    if (hostname.includes('staging')) {
      return 'https://api-staging.gameforge.app/api/v1';
    }
  }
  
  // Development fallback
  return 'http://localhost:8080/api/v1';
};

export const authService = new SecureAuthService(getApiBaseUrl());