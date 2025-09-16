/**
 * User roles and permissions type definitions for GameForge frontend
 * Compatible with GF_Database PostgreSQL schema
 */

export interface User {
  id: string;
  email: string;
  name: string;
  username: string;
  role: UserRole;
  permissions?: Permission[];
  avatar?: string;
  createdAt: string;
  lastLoginAt?: string;
  dataClassification?: string;
  encryptionRequired?: boolean;
}

// GF_Database Compatible User Roles (5 roles exactly as defined in GF_Database)
export type UserRole = 
  | 'basic_user'
  | 'premium_user'
  | 'ai_user'
  | 'admin'
  | 'super_admin';

// GF_Database Compatible Permissions (19 permissions exactly as defined in GF_Database)
export type Permission = 
  // Asset permissions (6 permissions)
  | 'assets:read'
  | 'assets:create'
  | 'assets:update' 
  | 'assets:delete'
  | 'assets:upload'
  | 'assets:download'
  
  // Project permissions (5 permissions)
  | 'projects:read'
  | 'projects:create'
  | 'projects:update'
  | 'projects:delete'
  | 'projects:share'
  
  // Model permissions (5 permissions)
  | 'models:read'
  | 'models:create'
  | 'models:update'
  | 'models:delete'
  | 'models:train'
  
  // Storage permissions (4 permissions)
  | 'storage:read'
  | 'storage:write'
  | 'storage:delete'
  | 'storage:admin'
  
  // AI generation permission (1 permission)
  | 'ai:generate'
  
  // Wildcard permissions for admins
  | 'assets:*'
  | 'projects:*'
  | 'models:*'
  | 'storage:*'
  | 'users:*'
  | 'system:*'
  | '*:*';

export interface AccessControlConfig {
  strictMode: boolean;
  debugMode: boolean;
  cachePermissions: boolean;
}

/**
 * Role-based permission mapping - MATCHES GF_Database auto-assignment
 */
export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  basic_user: [
    'assets:read', 
    'projects:read', 
    'projects:create'
  ],
  
  premium_user: [
    'assets:read', 'assets:create', 'assets:update',
    'projects:read', 'projects:create', 'projects:update', 
    'models:read', 'models:create'
  ],
  
  ai_user: [
    'assets:read', 'assets:create', 'assets:update',
    'projects:read', 'projects:create', 'projects:update',
    'models:read', 'models:create', 'models:train',
    'ai:generate'
  ],
  
  admin: [
    'assets:*', 'projects:*', 'models:*', 'users:*', 'system:*'
  ],
  
  super_admin: [
    '*:*'
  ]
};

/**
 * Data classification types for GDPR/CCPA compliance
 */
export type DataClassification =
  | 'USER_IDENTITY' | 'USER_AUTH' | 'USER_PREFERENCES' | 'USER_ACTIVITY'
  | 'PAYMENT_DATA' | 'BILLING_INFO' | 'TRANSACTION_RECORDS'
  | 'PROJECT_METADATA' | 'ASSET_METADATA' | 'ASSET_BINARIES'
  | 'MODEL_ARTIFACTS' | 'TRAINING_DATASETS' | 'MODEL_METADATA' | 'AI_GENERATED_CONTENT'
  | 'APPLICATION_LOGS' | 'ACCESS_LOGS' | 'AUDIT_LOGS' | 'SYSTEM_METRICS'
  | 'API_KEYS' | 'ENCRYPTION_KEYS' | 'TLS_CERTIFICATES' | 'VAULT_TOKENS'
  | 'USAGE_ANALYTICS' | 'BUSINESS_METRICS' | 'PERFORMANCE_METRICS';

export interface ResourceOwnership {
  userId: string;
  resourceType: 'project' | 'asset' | 'model' | 'dataset';
  resourceId: string;
}

export interface PermissionContext {
  user: User;
  resource?: ResourceOwnership;
  strictMode?: boolean;
  debugMode?: boolean;
}

export interface StorageAccessToken {
  token: string;
  expiresAt: string;
  allowedActions: string[];
  resourceType: string;
  resourceId?: string;
}

export interface PresignedURL {
  url: string;
  method: string;
  headers: Record<string, string>;
  expiresAt: string;
  resourceId: string;
}

export function hasPermission(user: User, permission: Permission): boolean {
  if (!user.permissions) {
    return false;
  }
  
  if (user.permissions.includes(permission)) {
    return true;
  }
  
  const [resource, action] = permission.split(':');
  const wildcardResourcePermission = `${resource}:*` as Permission;
  if (user.permissions.includes(wildcardResourcePermission)) {
    return true;
  }
  
  if (user.permissions.includes('*:*')) {
    return true;
  }
  
  return false;
}

export function getUserPermissions(role: UserRole): Permission[] {
  return ROLE_PERMISSIONS[role] || [];
}

export function isValidRole(role: string): role is UserRole {
  return ['basic_user', 'premium_user', 'ai_user', 'admin', 'super_admin'].includes(role);
}