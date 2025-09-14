/**
 * Permission-Aware UI Components for GameForge
 * 
 * These components automatically handle role-based visibility and access control.
 * They mirror the backend security model in the frontend UI.
 */

import React from 'react';
import { useAccessControl } from '../hooks/useAccessControl';
import { Permission, UserRole, ResourceOwnership } from '../types/permissions';
import { Button } from './ui/button';

// ============================================================================
// Type Definitions
// ============================================================================

interface AccessControlledProps {
  children: React.ReactNode;
  permission?: Permission;
  permissions?: Permission[];
  requireAll?: boolean;
  role?: UserRole;
  roles?: UserRole[];
  resource?: ResourceOwnership;
  fallback?: React.ReactNode;
  debug?: boolean;
}

interface PermissionGateProps {
  children: React.ReactNode;
  permission?: Permission;
  permissions?: Permission[];
  requireAll?: boolean;
  resource?: ResourceOwnership;
  fallback?: React.ReactNode;
}

interface RoleGateProps {
  children: React.ReactNode;
  role?: UserRole;
  roles?: UserRole[];
  requireAll?: boolean;
  fallback?: React.ReactNode;
}

interface SecureButtonProps {
  children: React.ReactNode;
  permission?: Permission;
  permissions?: Permission[];
  requireAll?: boolean;
  role?: UserRole;
  roles?: UserRole[];
  resource?: ResourceOwnership;
  fallback?: React.ReactNode;
  disabledMessage?: string;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  className?: string;
  disabled?: boolean;
  title?: string;
  onClick?: () => void;
}

type AssetAction = 'view' | 'edit' | 'delete' | 'download' | 'share';
type AssetType = 'texture' | 'model' | 'animation' | 'sound' | 'script' | 'project';

interface AssetActionButtonProps extends Omit<SecureButtonProps, 'permission' | 'resource'> {
  action: AssetAction;
  assetId: string;
  assetType: AssetType;
  isOwner?: boolean;
}

type ProjectAction = 'view' | 'edit' | 'delete' | 'manage' | 'export';

interface ProjectActionButtonProps extends Omit<SecureButtonProps, 'permission' | 'resource'> {
  action: ProjectAction;
  projectId: string;
  isOwner?: boolean;
}

type AIFeature = 'generate' | 'train' | 'deploy' | 'monitor';

interface AIFeatureGateProps {
  children: React.ReactNode;
  feature: AIFeature;
  fallback?: React.ReactNode;
}

// ============================================================================
// Main Component - wrapper for permission/role-based access control
// ============================================================================

const AccessControlled: React.FC<AccessControlledProps> = ({
  children,
  permission,
  permissions,
  requireAll = false,
  role,
  roles,
  resource,
  fallback = null,
  debug = false
}) => {
  const { hasPermission, hasAllPermissions, hasAnyPermission, hasRole, hasAnyRole } = useAccessControl();

  if (debug) {
    console.log('AccessControlled Debug:', {
      permission,
      permissions,
      role,
      roles,
      resource,
      requireAll
    });
  }

  // Check if we have the required permission(s)
  if (permission || permissions) {
    let hasRequiredPermission = false;
    
    if (permission) {
      hasRequiredPermission = hasPermission(permission, undefined, resource);
    } else if (permissions) {
      hasRequiredPermission = requireAll 
        ? hasAllPermissions(permissions, undefined, resource)
        : hasAnyPermission(permissions, undefined, resource);
    }

    if (!hasRequiredPermission) {
      return <>{fallback}</>;
    }
  }

  // Check if we have the required role(s)
  if (role || roles) {
    let hasRequiredRole = false;
    
    if (role) {
      hasRequiredRole = hasRole(role);
    } else if (roles) {
      hasRequiredRole = requireAll
        ? roles.every(r => hasRole(r))
        : hasAnyRole(roles);
    }

    if (!hasRequiredRole) {
      return <>{fallback}</>;
    }
  }

  return <>{children}</>;
};

// ============================================================================
// Permission Gate - simpler interface for permission checking
// ============================================================================

const PermissionGate: React.FC<PermissionGateProps> = ({
  children,
  permission,
  permissions,
  requireAll = false,
  resource,
  fallback = null
}) => {
  return (
    <AccessControlled
      permission={permission}
      permissions={permissions}
      requireAll={requireAll}
      resource={resource}
      fallback={fallback}
    >
      {children}
    </AccessControlled>
  );
};

// ============================================================================
// Role Gate - simpler interface for role checking
// ============================================================================

const RoleGate: React.FC<RoleGateProps> = ({
  children,
  role,
  roles,
  requireAll = false,
  fallback = null
}) => {
  return (
    <AccessControlled
      role={role}
      roles={roles}
      requireAll={requireAll}
      fallback={fallback}
    >
      {children}
    </AccessControlled>
  );
};

// ============================================================================
// Secure Button - Button with built-in permission checking
// ============================================================================

const SecureButton: React.FC<SecureButtonProps> = ({
  children,
  permission,
  permissions,
  requireAll = false,
  role,
  roles,
  resource,
  fallback = null,
  disabledMessage,
  variant = 'default',
  size = 'default',
  className,
  disabled = false,
  title,
  onClick
}) => {
  const { hasPermission, hasAllPermissions, hasAnyPermission, hasRole, hasAnyRole } = useAccessControl();

  // Check permissions first
  let hasAccess = true;
  
  if (permission || permissions) {
    if (permission) {
      hasAccess = hasPermission(permission, undefined, resource);
    } else if (permissions) {
      hasAccess = requireAll 
        ? hasAllPermissions(permissions, undefined, resource)
        : hasAnyPermission(permissions, undefined, resource);
    }
  }
  
  if (hasAccess && (role || roles)) {
    if (role) {
      hasAccess = hasRole(role);
    } else if (roles) {
      hasAccess = requireAll
        ? roles.every(r => hasRole(r))
        : hasAnyRole(roles);
    }
  }

  if (!hasAccess) {
    return <>{fallback}</>;
  }

  const isDisabled = disabled;
  const buttonTitle = isDisabled && disabledMessage ? disabledMessage : title;

  return (
    <Button
      variant={variant}
      size={size}
      className={className}
      disabled={isDisabled}
      title={buttonTitle}
      onClick={onClick}
    >
      {children}
    </Button>
  );
};

// ============================================================================
// Asset Action Button - Specialized button for asset operations
// ============================================================================

const AssetActionButton: React.FC<AssetActionButtonProps> = ({
  children,
  action,
  assetId,
  assetType,
  isOwner = false,
  fallback = null,
  ...buttonProps
}) => {
  const getPermissionForAction = (action: AssetAction): Permission => {
    switch (action) {
      case 'view': return 'assets:read';
      case 'edit': return 'assets:update';
      case 'delete': return 'assets:delete';
      case 'download': return 'assets:download';
      case 'share': return 'projects:share';
      default: return 'assets:read';
    }
  };

  const permission = getPermissionForAction(action);
  const resource: ResourceOwnership = {
    userId: '', // Will be filled by useAccessControl
    resourceType: assetType as 'asset',
    resourceId: assetId
  };

  return (
    <SecureButton
      permission={permission}
      resource={resource}
      fallback={fallback}
      {...buttonProps}
    >
      {children}
    </SecureButton>
  );
};

// ============================================================================
// Project Action Button - Specialized button for project operations
// ============================================================================

const ProjectActionButton: React.FC<ProjectActionButtonProps> = ({
  children,
  action,
  projectId,
  isOwner = false,
  fallback = null,
  ...buttonProps
}) => {
  const getPermissionForAction = (action: ProjectAction): Permission => {
    switch (action) {
      case 'view': return 'projects:read';
      case 'edit': return 'projects:update';
      case 'delete': return 'projects:delete';
      case 'manage': return 'projects:update';
      case 'export': return 'projects:read';
      default: return 'projects:read';
    }
  };

  const permission = getPermissionForAction(action);
  const resource: ResourceOwnership = {
    userId: '', // Will be filled by useAccessControl
    resourceType: 'project',
    resourceId: projectId
  };

  return (
    <SecureButton
      permission={permission}
      resource={resource}
      fallback={fallback}
      {...buttonProps}
    >
      {children}
    </SecureButton>
  );
};

// ============================================================================
// AI Feature Gate - Gate for AI-related features
// ============================================================================

const AIFeatureGate: React.FC<AIFeatureGateProps> = ({
  children,
  feature,
  fallback = null
}) => {
  const getPermissionForFeature = (feature: AIFeature): Permission => {
    switch (feature) {
      case 'generate': return 'ai:generate';
      case 'train': return 'models:train';
      case 'deploy': return 'models:create';
      case 'monitor': return 'models:read';
      default: return 'ai:generate';
    }
  };

  return (
    <PermissionGate
      permission={getPermissionForFeature(feature)}
      fallback={fallback}
    >
      {children}
    </PermissionGate>
  );
};

// ============================================================================
// Admin Gate - Simple gate for admin-only features
// ============================================================================

const AdminGate: React.FC<{ children: React.ReactNode; fallback?: React.ReactNode }> = ({
  children,
  fallback = null
}) => {
  return (
    <RoleGate role="admin" fallback={fallback}>
      {children}
    </RoleGate>
  );
};

// ============================================================================
// Premium Gate - Simple gate for premium features
// ============================================================================

const PremiumGate: React.FC<{ children: React.ReactNode; fallback?: React.ReactNode }> = ({
  children,
  fallback = null
}) => {
  return (
    <RoleGate 
      roles={['admin', 'premium_user']} 
      fallback={fallback}
    >
      {children}
    </RoleGate>
  );
};

// ============================================================================
// Export all components
// ============================================================================

export {
  // Core components
  AccessControlled,
  PermissionGate,
  RoleGate,
  
  // Interactive components
  SecureButton,
  
  // Specialized components
  AssetActionButton,
  ProjectActionButton,
  
  // Feature gates
  AIFeatureGate,
  AdminGate,
  PremiumGate
};

// Type exports for external usage
export type {
  AccessControlledProps,
  PermissionGateProps,
  RoleGateProps,
  SecureButtonProps,
  AssetActionButtonProps,
  ProjectActionButtonProps,
  AIFeatureGateProps,
  AssetAction,
  AssetType,
  ProjectAction,
  AIFeature
};