/**
 * GameForge Centralized API Service
 * =================================
 * 
 * Single point for all API calls with centralized configuration,
 * authentication, error handling, and token management.
 * 
 * Security Features:
 * - Environment-based API configuration (no hardcoded URLs)
 * - Centralized authentication token handling
 * - Standardized error handling and reporting
 * - Request/response interceptors for debugging
 * - Automatic retry logic for failed requests
 */

// Configuration from environment variables
const config = {
  // Main GameForge API
  gameforgeApi: (() => {
    const url = (import.meta as any).env?.VITE_GAMEFORGE_API_URL;
    if (!url) {
      console.warn('VITE_GAMEFORGE_API_URL not configured, API calls may fail');
      return 'http://localhost:8080/api/v1'; // Updated backend port and API path
    }
    return url;
  })(),
  
  // AI Services APIs  
  inferenceApi: (() => {
    const url = (import.meta as any).env?.VITE_INFERENCE_API_URL;
    if (!url) {
      console.warn('VITE_INFERENCE_API_URL not configured, inference calls may fail');
      return 'http://localhost:8000'; // Temporary fallback for development
    }
    return url;
  })(),
  
  superresApi: (() => {
    const url = (import.meta as any).env?.VITE_SUPERRES_API_URL;
    if (!url) {
      console.warn('VITE_SUPERRES_API_URL not configured, super-resolution calls may fail');
      return 'http://localhost:8001'; // Temporary fallback for development
    }
    return url;
  })(),
  
  // Request timeouts
  defaultTimeout: 30000, // 30 seconds
  uploadTimeout: 120000,  // 2 minutes for file uploads
  
  // Retry configuration
  maxRetries: 3,
  retryDelay: 1000, // 1 second
};

// Standard API response interface
export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    message: string;
    details?: string;
    code?: string;
  };
  meta?: {
    timestamp: string;
    requestId?: string;
  };
}

// Request configuration interface
export interface RequestConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  body?: any;
  timeout?: number;
  retries?: number;
  requireAuth?: boolean;
}

// Error types for better error handling
export class APIError extends Error {
  constructor(
    message: string,
    public code?: string,
    public status?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export class NetworkError extends Error {
  constructor(message: string, public originalError?: Error) {
    super(message);
    this.name = 'NetworkError';
  }
}

export class AuthenticationError extends Error {
  constructor(message: string = 'Authentication required') {
    super(message);
    this.name = 'AuthenticationError';
  }
}

/**
 * Centralized API Client Class
 */
class APIClient {
  private baseUrl: string;
  private authToken: string | null = null;
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
    
    // Load token from localStorage on initialization
    this.loadAuthToken();
  }
  
  /**
   * Load authentication token from localStorage
   */
  private loadAuthToken(): void {
    try {
      this.authToken = localStorage.getItem('token');
    } catch (error) {
      console.warn('Failed to load auth token from localStorage:', error);
    }
  }
  
  /**
   * Set authentication token
   */
  setAuthToken(token: string | null): void {
    this.authToken = token;
    
    try {
      if (token) {
        localStorage.setItem('token', token);
      } else {
        localStorage.removeItem('token');
      }
    } catch (error) {
      console.warn('Failed to save auth token to localStorage:', error);
    }
  }
  
  /**
   * Get current authentication token
   */
  getAuthToken(): string | null {
    return this.authToken;
  }
  
  /**
   * Build request headers with authentication and defaults
   */
  private buildHeaders(customHeaders: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...customHeaders,
    };
    
    // Add authentication if available
    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }
    
    return headers;
  }
  
  /**
   * Create AbortController for request timeout
   */
  private createTimeoutController(timeout: number): AbortController {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), timeout);
    return controller;
  }
  
  /**
   * Parse response based on content type
   */
  private async parseResponse(response: Response): Promise<any> {
    const contentType = response.headers.get('content-type');
    
    if (contentType?.includes('application/json')) {
      return await response.json();
    } else if (contentType?.includes('text/')) {
      return await response.text();
    } else {
      return await response.blob();
    }
  }
  
  /**
   * Make HTTP request with retry logic
   */
  private async makeRequest<T>(
    endpoint: string, 
    requestConfig: RequestConfig = {}
  ): Promise<APIResponse<T>> {
    const {
      method = 'GET',
      headers: customHeaders = {},
      body,
      timeout = config.defaultTimeout,
      retries = config.maxRetries,
      requireAuth = true
    } = requestConfig;
    
    // Check authentication requirement
    if (requireAuth && !this.authToken) {
      throw new AuthenticationError('Authentication token required');
    }
    
    const url = `${this.baseUrl}${endpoint}`;
    const headers = this.buildHeaders(customHeaders);
    
    let lastError: Error | null = null;
    
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const controller = this.createTimeoutController(timeout);
        
        const fetchConfig: RequestInit = {
          method,
          headers,
          signal: controller.signal,
        };
        
        // Add body for non-GET requests
        if (method !== 'GET' && body !== undefined) {
          if (body instanceof FormData) {
            // Remove Content-Type for FormData (browser sets it with boundary)
            delete headers['Content-Type'];
            fetchConfig.body = body;
          } else if (typeof body === 'string') {
            fetchConfig.body = body;
          } else {
            fetchConfig.body = JSON.stringify(body);
          }
        }
        
        console.log(`🌐 API Request [${method}]: ${url}`, {
          headers: { ...headers, Authorization: headers.Authorization ? '[REDACTED]' : undefined },
          body: body instanceof FormData ? '[FormData]' : body
        });
        
        const response = await fetch(url, fetchConfig);
        
        // Handle different response status codes
        if (response.ok) {
          const data = await this.parseResponse(response);
          
          console.log(`✅ API Success [${response.status}]: ${url}`, data);
          
          return {
            success: true,
            data,
            meta: {
              timestamp: new Date().toISOString(),
              requestId: response.headers.get('x-request-id') || undefined
            }
          };
        } else {
          // Handle API errors
          let errorData: any = {};
          try {
            errorData = await this.parseResponse(response);
          } catch (parseError) {
            console.warn('Failed to parse error response:', parseError);
          }
          
          const apiError = new APIError(
            errorData.message || `HTTP ${response.status}: ${response.statusText}`,
            errorData.code || response.status.toString(),
            response.status,
            errorData
          );
          
          console.error(`❌ API Error [${response.status}]: ${url}`, apiError);
          
          // Don't retry certain error types
          if (response.status === 401 || response.status === 403 || response.status === 404) {
            throw apiError;
          }
          
          lastError = apiError;
        }
      } catch (error) {
        console.error(`💥 Request failed (attempt ${attempt + 1}/${retries + 1}):`, error);
        
        if (error instanceof APIError || error instanceof AuthenticationError) {
          throw error;
        }
        
        if (error instanceof Error && error.name === 'AbortError') {
          lastError = new NetworkError('Request timeout', error);
        } else {
          lastError = new NetworkError('Network request failed', error as Error);
        }
        
        // Don't retry on timeout or auth errors
        if (error instanceof AuthenticationError || (error as any)?.name === 'AbortError') {
          break;
        }
      }
      
      // Wait before retry (exponential backoff)
      if (attempt < retries) {
        const delay = config.retryDelay * Math.pow(2, attempt);
        console.log(`⏳ Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
    
    // If all retries failed, throw the last error
    if (lastError) {
      throw lastError;
    }
    
    throw new NetworkError('Unknown network error');
  }
  
  // Convenience methods for different HTTP verbs
  async get<T>(endpoint: string, config?: Omit<RequestConfig, 'method'>): Promise<APIResponse<T>> {
    return this.makeRequest<T>(endpoint, { ...config, method: 'GET' });
  }
  
  async post<T>(endpoint: string, body?: any, config?: Omit<RequestConfig, 'method' | 'body'>): Promise<APIResponse<T>> {
    return this.makeRequest<T>(endpoint, { ...config, method: 'POST', body });
  }
  
  async put<T>(endpoint: string, body?: any, config?: Omit<RequestConfig, 'method' | 'body'>): Promise<APIResponse<T>> {
    return this.makeRequest<T>(endpoint, { ...config, method: 'PUT', body });
  }
  
  async delete<T>(endpoint: string, config?: Omit<RequestConfig, 'method'>): Promise<APIResponse<T>> {
    return this.makeRequest<T>(endpoint, { ...config, method: 'DELETE' });
  }
  
  async patch<T>(endpoint: string, body?: any, config?: Omit<RequestConfig, 'method' | 'body'>): Promise<APIResponse<T>> {
    return this.makeRequest<T>(endpoint, { ...config, method: 'PATCH', body });
  }
}

// Create singleton instances for different APIs
export const gameforgeAPI = new APIClient(config.gameforgeApi);
export const inferenceAPI = new APIClient(config.inferenceApi);
export const superresAPI = new APIClient(config.superresApi);

// Export main API client as default
export default gameforgeAPI;

// Centralized authentication management
export const AuthAPI = {
  /**
   * Login with email and password
   */
  async login(email: string, password: string): Promise<APIResponse<{ token: string; user: any }>> {
    const response = await gameforgeAPI.post<{ token: string; user: any }>('/auth/login', 
      { email, password }, 
      { requireAuth: false }
    );
    
    if (response.success && response.data?.token) {
      gameforgeAPI.setAuthToken(response.data.token);
      inferenceAPI.setAuthToken(response.data.token);
      superresAPI.setAuthToken(response.data.token);
    }
    
    return response;
  },
  
  /**
   * Register new user
   */
  async register(email: string, password: string, name?: string): Promise<APIResponse<{ token: string; user: any }>> {
    const response = await gameforgeAPI.post<{ token: string; user: any }>('/auth/register', 
      { email, password, name }, 
      { requireAuth: false }
    );
    
    if (response.success && response.data?.token) {
      gameforgeAPI.setAuthToken(response.data.token);
      inferenceAPI.setAuthToken(response.data.token);
      superresAPI.setAuthToken(response.data.token);
    }
    
    return response;
  },
  
  /**
   * Logout user
   */
  async logout(): Promise<void> {
    try {
      await gameforgeAPI.post('/auth/logout');
    } catch (error) {
      console.warn('Logout API call failed:', error);
    } finally {
      // Clear tokens regardless of API call success
      gameforgeAPI.setAuthToken(null);
      inferenceAPI.setAuthToken(null);
      superresAPI.setAuthToken(null);
    }
  },
  
  /**
   * Redirect to OAuth provider
   */
  redirectToOAuth(provider: 'github' | 'google'): void {
    const redirectUrl = `${config.gameforgeApi}/auth/${provider}`;
    console.log(`🔗 Redirecting to OAuth: ${redirectUrl}`);
    window.location.href = redirectUrl;
  },
  
  /**
   * Update user profile
   */
  async updateProfile(profileData: { name?: string }): Promise<APIResponse<{ user: any; access_token: string; token_type: string }>> {
    const response = await gameforgeAPI.patch<{ user: any; access_token: string; token_type: string }>('/auth/me', 
      profileData,
      { requireAuth: true }
    );
    
    // Update the token if a new one is provided
    if (response.success && response.data?.access_token) {
      gameforgeAPI.setAuthToken(response.data.access_token);
      inferenceAPI.setAuthToken(response.data.access_token);
      superresAPI.setAuthToken(response.data.access_token);
    }
    
    return response;
  },
  
  /**
   * Set authentication token for all APIs
   */
  setToken(token: string | null): void {
    gameforgeAPI.setAuthToken(token);
    inferenceAPI.setAuthToken(token);
    superresAPI.setAuthToken(token);
  },
  
  /**
   * Get current authentication token
   */
  getToken(): string | null {
    return gameforgeAPI.getAuthToken();
  }
};

// AI Generation API - uses centralized endpoints
export const AIAPI = {
  /**
   * Generate AI assets
   */
  async generateAsset(request: any): Promise<APIResponse> {
    return gameforgeAPI.post('/ai/generate', request);
  },
  
  /**
   * Get generation job status
   */
  async getJobStatus(jobId: string): Promise<APIResponse> {
    return gameforgeAPI.get(`/ai/job/${jobId}`);
  },
  
  /**
   * Generate story content
   */
  async generateStory(request: any): Promise<APIResponse> {
    return gameforgeAPI.post('/ai/story', request);
  }
};

// Export configuration for components that need it
export { config };

// Utility function to check if error requires re-authentication
export function requiresReauth(error: any): boolean {
  return error instanceof AuthenticationError || 
         (error instanceof APIError && error.status === 401);
}

// Utility function to format API errors for UI display
export function formatAPIError(error: any): string {
  if (error instanceof APIError) {
    return error.message;
  } else if (error instanceof NetworkError) {
    return 'Network connection failed. Please check your internet connection.';
  } else if (error instanceof AuthenticationError) {
    return 'Please log in to continue.';
  } else {
    return 'An unexpected error occurred. Please try again.';
  }
}