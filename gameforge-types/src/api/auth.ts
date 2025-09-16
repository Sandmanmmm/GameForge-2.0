/**
 * Authentication API Types
 * 
 * IMPORTANT: Never include actual tokens in these types.
 * Tokens should only be handled client-side after successful authentication.
 */

import { ApiResponse } from './common';
import { UserRole } from './permissions';

export interface User {
  id: string;
  email: string;
  name: string;
  username?: string;
  roles: UserRole[];
  permissions?: string[];
  profile?: UserProfile;
  createdAt: string;
  updatedAt: string;
  lastLoginAt?: string;
  isActive: boolean;
  dataClassification?: string;
  encryptionRequired?: boolean;
}

export interface UserProfile {
  avatar?: string;
  bio?: string;
  company?: string;
  location?: string;
  website?: string;
  preferences: UserPreferences;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  timezone: string;
  notifications: NotificationSettings;
}

export interface NotificationSettings {
  email: boolean;
  push: boolean;
  marketing: boolean;
  security: boolean;
}

// Request/Response types (NO TOKENS HERE)
export interface LoginRequest {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  acceptTerms: boolean;
}

export interface AuthResponse {
  user: User;
  // Token is handled separately by the client
  expiresAt: string;
}

export interface UpdateProfileRequest {
  name?: string;
  profile?: Partial<UserProfile>;
}

export interface ChangePasswordRequest {
  currentPassword: string;
  newPassword: string;
}

export interface ResetPasswordRequest {
  email: string;
}

export interface ConfirmResetPasswordRequest {
  token: string;
  newPassword: string;
}

// OAuth types
export interface OAuthProvider {
  name: string;
  displayName: string;
  authUrl: string;
  enabled: boolean;
}

export interface OAuthCallback {
  code: string;
  state?: string;
  provider: string;
}

// API response types
export type LoginResponse = ApiResponse<AuthResponse>;
export type RegisterResponse = ApiResponse<AuthResponse>;
export type ProfileResponse = ApiResponse<User>;
export type OAuthProvidersResponse = ApiResponse<OAuthProvider[]>;