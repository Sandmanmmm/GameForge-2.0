/**
 * User roles and permissions type definitions for GameForge frontend
 */

export interface User {
  id: string;
  email: string;
  name: string;
  roles: UserRole[];
  permissions?: string[];
  avatar?: string;
  createdAt: string;
  lastLoginAt?: string;
}

export type UserRole = 
  | 'admin'           // Full system access
  | 'premium_user'    // Premium features access  
  | 'ai_user'         // AI generation access
  | 'basic_user'      // Basic read-only access
  | 'ml_engineer'     // Model management access
  | 'viewer';         // View-only access

export type Permission = 
  // Storage permissions
  | 'storage:read'
  | 'storage:write'
  | 'storage:delete'
  | 'storage:admin'
  
  // Asset permissions
  | 'assets:read'
  | 'assets:create'
  | 'assets:update' 
  | 'assets:delete'
  | 'assets:download'
  | 'assets:upload'
  
  // AI generation permissions
  | 'ai:generate'
  | 'ai:superres'
  | 'ai:style_transfer'
  | 'ai:advanced'
  
  // Project permissions
  | 'projects:read'
  | 'projects:create'
  | 'projects:update'
  | 'projects:delete'
  | 'projects:share'
  
  // Model permissions
  | 'models:read'
  | 'models:create'
  | 'models:update'
  | 'models:delete'
  | 'models:train'
  
  // Admin permissions
  | 'admin:users'
  | 'admin:system'
  | 'admin:security'
  | 'admin:analytics';

export interface AccessControlConfig {
  strictMode: boolean;          // If true, deny by default
  debugMode: boolean;          // Enable permission debugging
  cachePermissions: boolean;   // Cache permission checks
}

/**
 * Role-based permission mapping
 * Maps user roles to their default permissions
 */
export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  admin: [
    // Full access to everything
    'storage:read', 'storage:write', 'storage:delete', 'storage:admin',
    'assets:read', 'assets:create', 'assets:update', 'assets:delete', 'assets:download', 'assets:upload',
    'ai:generate', 'ai:superres', 'ai:style_transfer', 'ai:advanced',
    'projects:read', 'projects:create', 'projects:update', 'projects:delete', 'projects:share',
    'models:read', 'models:create', 'models:update', 'models:delete', 'models:train',
    'admin:users', 'admin:system', 'admin:security', 'admin:analytics'
  ],
  
  premium_user: [
    'storage:read', 'storage:write', 'storage:delete',
    'assets:read', 'assets:create', 'assets:update', 'assets:delete', 'assets:download', 'assets:upload',
    'ai:generate', 'ai:superres', 'ai:style_transfer', 'ai:advanced',
    'projects:read', 'projects:create', 'projects:update', 'projects:delete', 'projects:share',
    'models:read', 'models:create', 'models:update'
  ],
  
  ai_user: [
    'storage:read', 'storage:write',
    'assets:read', 'assets:create', 'assets:update', 'assets:download', 'assets:upload',
    'ai:generate', 'ai:superres', 'ai:style_transfer',
    'projects:read', 'projects:create', 'projects:update', 'projects:share',
    'models:read'
  ],
  
  basic_user: [
    'storage:read',
    'assets:read', 'assets:download',
    'projects:read', 'projects:create', 'projects:update',
    'models:read'
  ],
  
  ml_engineer: [
    'storage:read', 'storage:write',
    'assets:read', 'assets:create', 'assets:update', 'assets:download', 'assets:upload',
    'ai:generate', 'ai:superres', 'ai:style_transfer', 'ai:advanced',
    'projects:read', 'projects:create', 'projects:update', 'projects:share',
    'models:read', 'models:create', 'models:update', 'models:delete', 'models:train'
  ],
  
  viewer: [
    'storage:read',
    'assets:read',
    'projects:read',
    'models:read'
  ]
};

/**
 * Resource ownership patterns
 * Define when users can access resources they own
 */
export interface ResourceOwnership {
  userId: string;
  resourceType: 'project' | 'asset' | 'model';
  resourceId: string;
}

/**
 * Permission check context
 */
export interface PermissionContext {
  user: User;
  resource?: ResourceOwnership;
  strictMode?: boolean;
  debugMode?: boolean;
}

/**
 * Permission check result
 */
export interface PermissionCheckResult {
  allowed: boolean;
  reason?: string;
  requiredRoles?: UserRole[];
  requiredPermissions?: Permission[];
  fallbackAction?: string;
}