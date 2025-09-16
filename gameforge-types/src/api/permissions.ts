/**
 * Permissions and Authorization Types
 * 
 * These types match exactly with the GF_Database schema for consistency.
 */

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
  
  // Storage permissions (3 permissions) 
  | 'storage:read'
  | 'storage:write'
  | 'storage:admin';

// Admin permissions - wildcards for administrative access
export type AdminPermission = 
  | 'assets:*'
  | 'projects:*'
  | 'models:*'
  | 'storage:*'
  | 'users:*'
  | 'system:*';

// Role-Permission Mapping (matches GF_Database auto-assignment)
export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  basic_user: [
    'assets:read', 
    'projects:read'
  ],
  premium_user: [
    'assets:read', 'assets:create', 'assets:upload', 'assets:download',
    'projects:read', 'projects:create', 'projects:update', 'projects:delete',
    'models:read'
  ],
  ai_user: [
    'assets:read', 'assets:create', 'assets:upload', 'assets:download',
    'projects:read', 'projects:create', 'projects:update', 'projects:delete', 'projects:share',
    'models:read', 'models:create', 'models:update', 'models:train',
    'storage:read', 'storage:write'
  ],
  admin: [
    'assets:read', 'assets:create', 'assets:update', 'assets:delete', 'assets:upload', 'assets:download',
    'projects:read', 'projects:create', 'projects:update', 'projects:delete', 'projects:share',
    'models:read', 'models:create', 'models:update', 'models:delete', 'models:train',
    'storage:read', 'storage:write', 'storage:admin'
  ],
  super_admin: [
    'assets:read', 'assets:create', 'assets:update', 'assets:delete', 'assets:upload', 'assets:download',
    'projects:read', 'projects:create', 'projects:update', 'projects:delete', 'projects:share',
    'models:read', 'models:create', 'models:update', 'models:delete', 'models:train',
    'storage:read', 'storage:write', 'storage:admin'
  ]
};

// Data classification for GDPR/CCPA compliance (23 types as per GF_Database)
export type DataClassification = 
  | 'public'
  | 'internal'
  | 'confidential'
  | 'restricted'
  | 'pii'
  | 'pii_sensitive'
  | 'pci'
  | 'hipaa'
  | 'financial'
  | 'legal'
  | 'hr'
  | 'marketing'
  | 'analytics'
  | 'logs'
  | 'backups'
  | 'temp'
  | 'archived'
  | 'deleted'
  | 'encrypted'
  | 'anonymized'
  | 'pseudonymized'
  | 'aggregated'
  | 'derived';

export interface ResourceOwnership {
  userId: string;
  resourceType: 'project' | 'asset' | 'model';
  resourceId: string;
}

export interface PermissionContext {
  user?: import('./auth').User;
  resource?: ResourceOwnership;
  action?: string;
}

export interface PermissionCheckResult {
  allowed: boolean;
  reason?: string;
  requiredRoles?: UserRole[];
  requiredPermissions?: Permission[];
  fallbackAction?: 'login' | 'upgrade' | 'contact';
}

export interface AccessControlConfig {
  strictMode: boolean;
  debugMode: boolean;
  cachePermissions: boolean;
}