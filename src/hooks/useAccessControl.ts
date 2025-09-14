/**
 * Access Control Hook for GameForge Frontend
 * 
 * Provides role-based permission checking that mirrors backend security.
 * Ensures UI elements are only shown when users have proper permissions.
 */

import { useContext, useMemo, useCallback } from 'react';
import { AuthContext } from '../contexts/AuthContext';
import { 
  User, 
  UserRole, 
  Permission, 
  ROLE_PERMISSIONS,
  PermissionContext,
  PermissionCheckResult,
  ResourceOwnership,
  AccessControlConfig
} from '../types/permissions';

// Default access control configuration
const DEFAULT_CONFIG: AccessControlConfig = {
  strictMode: true,      // Deny by default for security
  debugMode: false,      // Enable in development
  cachePermissions: true // Cache for performance
};

/**
 * Permission cache for performance
 */
const permissionCache = new Map<string, boolean>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes
const cacheTimestamps = new Map<string, number>();

/**
 * Main access control hook
 */
export const useAccessControl = (config: Partial<AccessControlConfig> = {}) => {
  const { user } = useContext(AuthContext);
  const finalConfig = { ...DEFAULT_CONFIG, ...config };

  /**
   * Get all permissions for a user based on their roles
   */
  const getUserPermissions = useCallback((targetUser: User): Permission[] => {
    if (!targetUser?.roles) return [];
    
    const permissions = new Set<Permission>();
    
    // Add role-based permissions
    targetUser.roles.forEach(role => {
      const rolePermissions = ROLE_PERMISSIONS[role] || [];
      rolePermissions.forEach(permission => permissions.add(permission));
    });
    
    // Add explicit permissions if any
    if (targetUser.permissions) {
      targetUser.permissions.forEach(permission => 
        permissions.add(permission as Permission)
      );
    }
    
    return Array.from(permissions);
  }, []);

  /**
   * Check if user has a specific permission
   */
  const hasPermission = useCallback((
    permission: Permission,
    targetUser?: User,
    resource?: ResourceOwnership
  ): boolean => {
    const checkUser = targetUser || user;
    if (!checkUser) return false;

    // Create cache key
    const cacheKey = `${checkUser.id}:${permission}:${resource?.resourceId || 'global'}`;
    
    // Check cache if enabled
    if (finalConfig.cachePermissions) {
      const cached = permissionCache.get(cacheKey);
      const timestamp = cacheTimestamps.get(cacheKey);
      
      if (cached !== undefined && timestamp && (Date.now() - timestamp) < CACHE_TTL) {
        return cached;
      }
    }

    // Admin always has access
    if (checkUser.roles?.includes('admin')) {
      const result = true;
      if (finalConfig.cachePermissions) {
        permissionCache.set(cacheKey, result);
        cacheTimestamps.set(cacheKey, Date.now());
      }
      return result;
    }

    // Check resource ownership for user-specific resources
    if (resource && resource.userId === checkUser.id) {
      // Users can access their own resources with reduced permissions
      const ownedResourcePermissions: Permission[] = [
        'assets:read', 'assets:update', 'assets:delete', 'assets:download',
        'projects:read', 'projects:update', 'projects:delete',
        'models:read', 'models:update'
      ];
      
      if (ownedResourcePermissions.includes(permission)) {
        const result = true;
        if (finalConfig.cachePermissions) {
          permissionCache.set(cacheKey, result);
          cacheTimestamps.set(cacheKey, Date.now());
        }
        return result;
      }
    }

    // Check role-based permissions
    const userPermissions = getUserPermissions(checkUser);
    const result = userPermissions.includes(permission);
    
    // Cache result
    if (finalConfig.cachePermissions) {
      permissionCache.set(cacheKey, result);
      cacheTimestamps.set(cacheKey, Date.now());
    }
    
    // Debug logging
    if (finalConfig.debugMode) {
      console.log(`🔐 Permission Check:`, {
        user: checkUser.id,
        permission,
        resource,
        userRoles: checkUser.roles,
        userPermissions,
        result
      });
    }

    return result;
  }, [user, getUserPermissions, finalConfig]);

  /**
   * Check if user has any of the specified permissions
   */
  const hasAnyPermission = useCallback((
    permissions: Permission[],
    targetUser?: User,
    resource?: ResourceOwnership
  ): boolean => {
    return permissions.some(permission => 
      hasPermission(permission, targetUser, resource)
    );
  }, [hasPermission]);

  /**
   * Check if user has all of the specified permissions
   */
  const hasAllPermissions = useCallback((
    permissions: Permission[],
    targetUser?: User,
    resource?: ResourceOwnership
  ): boolean => {
    return permissions.every(permission => 
      hasPermission(permission, targetUser, resource)
    );
  }, [hasPermission]);

  /**
   * Check if user has a specific role
   */
  const hasRole = useCallback((
    role: UserRole,
    targetUser?: User
  ): boolean => {
    const checkUser = targetUser || user;
    return checkUser?.roles?.includes(role) || false;
  }, [user]);

  /**
   * Check if user has any of the specified roles
   */
  const hasAnyRole = useCallback((
    roles: UserRole[],
    targetUser?: User
  ): boolean => {
    const checkUser = targetUser || user;
    if (!checkUser?.roles) return false;
    return roles.some(role => checkUser.roles.includes(role));
  }, [user]);

  /**
   * Comprehensive permission check with detailed result
   */
  const checkPermission = useCallback((
    permission: Permission,
    context: Partial<PermissionContext> = {}
  ): PermissionCheckResult => {
    const checkUser = context.user || user;
    
    if (!checkUser) {
      return {
        allowed: false,
        reason: 'User not authenticated',
        fallbackAction: 'login'
      };
    }

    const hasAccess = hasPermission(permission, checkUser, context.resource);
    
    if (hasAccess) {
      return {
        allowed: true
      };
    }

    // Determine what's needed for access
    const requiredRoles: UserRole[] = [];
    const requiredPermissions: Permission[] = [permission];
    
    // Find roles that have this permission
    Object.entries(ROLE_PERMISSIONS).forEach(([role, permissions]) => {
      if (permissions.includes(permission)) {
        requiredRoles.push(role as UserRole);
      }
    });

    return {
      allowed: false,
      reason: `Missing permission: ${permission}`,
      requiredRoles,
      requiredPermissions,
      fallbackAction: 'upgrade'
    };
  }, [user, hasPermission]);

  /**
   * Check if user can perform action on resource
   */
  const canPerformAction = useCallback((
    action: string,
    resourceType: 'asset' | 'project' | 'model' | 'storage',
    resourceId?: string,
    resourceUserId?: string
  ): boolean => {
    // Map action + resource type to permission
    const permissionMap: Record<string, Permission> = {
      'read:asset': 'assets:read',
      'create:asset': 'assets:create', 
      'update:asset': 'assets:update',
      'delete:asset': 'assets:delete',
      'download:asset': 'assets:download',
      'upload:asset': 'assets:upload',
      
      'read:project': 'projects:read',
      'create:project': 'projects:create',
      'update:project': 'projects:update', 
      'delete:project': 'projects:delete',
      'share:project': 'projects:share',
      
      'read:model': 'models:read',
      'create:model': 'models:create',
      'update:model': 'models:update',
      'delete:model': 'models:delete',
      'train:model': 'models:train',
      
      'read:storage': 'storage:read',
      'write:storage': 'storage:write',
      'delete:storage': 'storage:delete',
      'admin:storage': 'storage:admin'
    };

    const permission = permissionMap[`${action}:${resourceType}`];
    if (!permission) return false;

    const resource: ResourceOwnership | undefined = 
      resourceId && resourceUserId ? {
        userId: resourceUserId,
        resourceType: resourceType as 'project' | 'asset' | 'model',
        resourceId
      } : undefined;

    return hasPermission(permission, user, resource);
  }, [hasPermission, user]);

  /**
   * Clear permission cache (useful after role changes)
   */
  const clearCache = useCallback(() => {
    permissionCache.clear();
    cacheTimestamps.clear();
  }, []);

  /**
   * Get user's current permissions list
   */
  const currentPermissions = useMemo(() => {
    return user ? getUserPermissions(user) : [];
  }, [user, getUserPermissions]);

  return {
    // Permission checks
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    checkPermission,
    canPerformAction,
    
    // Role checks
    hasRole,
    hasAnyRole,
    
    // Utilities
    getUserPermissions,
    clearCache,
    
    // Current user state
    user,
    currentPermissions,
    isAuthenticated: !!user,
    
    // Configuration
    config: finalConfig
  };
};

/**
 * Hook for checking specific permission (convenience hook)
 */
export const usePermission = (permission: Permission, resource?: ResourceOwnership) => {
  const { hasPermission, user } = useAccessControl();
  return hasPermission(permission, user, resource);
};

/**
 * Hook for checking multiple permissions
 */
export const usePermissions = (permissions: Permission[], requireAll = false) => {
  const { hasAllPermissions, hasAnyPermission, user } = useAccessControl();
  
  if (requireAll) {
    return hasAllPermissions(permissions, user);
  }
  
  return hasAnyPermission(permissions, user);
};

/**
 * Hook for checking user role
 */
export const useRole = (role: UserRole) => {
  const { hasRole } = useAccessControl();
  return hasRole(role);
};

/**
 * Hook for role-based conditional rendering
 */
export const useRoleGate = (allowedRoles: UserRole[]) => {
  const { hasAnyRole, user } = useAccessControl();
  return {
    allowed: hasAnyRole(allowedRoles, user),
    user,
    roles: user?.roles || []
  };
};