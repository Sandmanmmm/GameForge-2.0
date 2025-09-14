/**
 * Example usage of Permission-Aware Components
 * This demonstrates how frontend UI automatically enforces backend security
 */

import React from 'react';
import {
  AccessControlled,
  PermissionGate, 
  RoleGate,
  SecureButton,
  AssetActionButton,
  ProjectActionButton,
  AIFeatureGate,
  AdminGate,
  PremiumGate
} from './AccessControl';

interface ExampleAssetCardProps {
  asset: {
    id: string;
    name: string;
    type: 'texture' | 'model' | 'animation';
    userId: string;
  };
  currentUserId: string;
}

/**
 * Example Asset Card with Permission-Aware Actions
 * Shows how buttons automatically hide based on user permissions
 */
export const ExampleAssetCard: React.FC<ExampleAssetCardProps> = ({ 
  asset, 
  currentUserId 
}) => {
  const isOwner = asset.userId === currentUserId;

  return (
    <div className="border rounded-lg p-4 space-y-4">
      {/* Asset Info - Always visible */}
      <div>
        <h3 className="font-semibold">{asset.name}</h3>
        <p className="text-sm text-gray-600">Type: {asset.type}</p>
        {isOwner && <span className="text-xs bg-blue-100 px-2 py-1 rounded">You own this</span>}
      </div>

      {/* Action Buttons - Automatically hidden if user lacks permissions */}
      <div className="flex gap-2 flex-wrap">
        {/* View button - visible for users with assets:read */}
        <AssetActionButton
          action="view"
          assetId={asset.id}
          assetType={asset.type}
          isOwner={isOwner}
          variant="outline"
          size="sm"
        >
          View
        </AssetActionButton>

        {/* Edit button - only visible if user has assets:update */}
        <AssetActionButton
          action="edit"
          assetId={asset.id}
          assetType={asset.type}
          isOwner={isOwner}
          variant="outline"
          size="sm"
          fallback={
            <span className="text-xs text-gray-400">Edit (No permission)</span>
          }
        >
          Edit
        </AssetActionButton>

        {/* Delete button - only visible if user has assets:delete */}
        <AssetActionButton
          action="delete"
          assetId={asset.id}
          assetType={asset.type}
          isOwner={isOwner}
          variant="destructive"
          size="sm"
          fallback={null} // Completely hidden if no permission
        >
          Delete
        </AssetActionButton>

        {/* Download button - visible for users with assets:read */}
        <AssetActionButton
          action="download"
          assetId={asset.id}
          assetType={asset.type}
          isOwner={isOwner}
          variant="secondary"
          size="sm"
        >
          Download
        </AssetActionButton>
      </div>

      {/* Premium Features - Only visible to premium/admin users */}
      <PremiumGate fallback={
        <div className="text-xs text-gray-400 italic">
          Premium features available with upgrade
        </div>
      }>
        <div className="bg-gradient-to-r from-purple-100 to-pink-100 p-3 rounded-lg">
          <p className="text-sm font-medium text-purple-800">Premium Features</p>
          <div className="flex gap-2 mt-2">
            <SecureButton
              permission="ai:superres"
              variant="outline"
              size="sm"
              className="text-purple-700 border-purple-300"
            >
              AI Upscale
            </SecureButton>
            <SecureButton
              permission="ai:style_transfer"
              variant="outline"
              size="sm"
              className="text-purple-700 border-purple-300"
            >
              Style Transfer
            </SecureButton>
          </div>
        </div>
      </PremiumGate>

      {/* AI Features Gate - Only shows if user has AI permissions */}
      <AIFeatureGate 
        feature="generate"
        fallback={
          <div className="text-xs text-gray-400 italic">
            AI generation requires ai_user role or higher
          </div>
        }
      >
        <div className="bg-green-50 p-3 rounded-lg">
          <p className="text-sm font-medium text-green-800">AI Generation</p>
          <SecureButton
            permission="ai:generate"
            variant="outline"
            size="sm"
            className="mt-2 text-green-700 border-green-300"
          >
            Generate Variations
          </SecureButton>
        </div>
      </AIFeatureGate>

      {/* Admin Only Section */}
      <AdminGate>
        <div className="bg-red-50 border border-red-200 p-3 rounded-lg">
          <p className="text-sm font-medium text-red-800">Admin Actions</p>
          <div className="flex gap-2 mt-2">
            <SecureButton
              permission="admin:system"
              variant="destructive"
              size="sm"
            >
              System Override
            </SecureButton>
            <SecureButton
              permission="assets:delete"
              variant="destructive"
              size="sm"
            >
              Force Delete
            </SecureButton>
          </div>
        </div>
      </AdminGate>
    </div>
  );
};

/**
 * Example Project Dashboard with Role-Based UI
 */
export const ExampleProjectDashboard: React.FC = () => {
  const exampleProject = {
    id: 'proj-123',
    name: 'My Game Project',
    userId: 'user-456'
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold">Project Dashboard</h2>
      
      {/* Project Actions */}
      <div className="border rounded-lg p-4">
        <h3 className="font-semibold mb-3">Project: {exampleProject.name}</h3>
        
        <div className="flex gap-2 flex-wrap">
          <ProjectActionButton
            action="view"
            projectId={exampleProject.id}
            variant="outline"
            size="sm"
          >
            View Project
          </ProjectActionButton>

          <ProjectActionButton
            action="edit"
            projectId={exampleProject.id}
            variant="outline"
            size="sm"
            fallback={
              <span className="text-xs text-gray-400">Edit (No permission)</span>
            }
          >
            Edit Project
          </ProjectActionButton>

          <ProjectActionButton
            action="delete"
            projectId={exampleProject.id}
            variant="destructive"
            size="sm"
            fallback={null}
          >
            Delete Project
          </ProjectActionButton>

          <ProjectActionButton
            action="export"
            projectId={exampleProject.id}
            variant="secondary"
            size="sm"
          >
            Export
          </ProjectActionButton>
        </div>
      </div>

      {/* Feature Gates Demo */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Basic User Features */}
        <PermissionGate 
          permission="projects:read"
          fallback={<div className="p-4 bg-gray-100 rounded">No project access</div>}
        >
          <div className="p-4 bg-blue-50 rounded">
            <h4 className="font-medium text-blue-800">Basic Features</h4>
            <p className="text-sm text-blue-600">View and create projects</p>
          </div>
        </PermissionGate>

        {/* AI User Features */}
        <RoleGate 
          roles={['ai_user', 'premium_user', 'admin']}
          fallback={<div className="p-4 bg-gray-100 rounded">Upgrade for AI features</div>}
        >
          <div className="p-4 bg-purple-50 rounded">
            <h4 className="font-medium text-purple-800">AI Features</h4>
            <p className="text-sm text-purple-600">Generate and enhance assets</p>
          </div>
        </RoleGate>

        {/* ML Engineer Features */}
        <RoleGate 
          role="ml_engineer"
          fallback={<div className="p-4 bg-gray-100 rounded">ML Engineer access required</div>}
        >
          <div className="p-4 bg-green-50 rounded">
            <h4 className="font-medium text-green-800">Model Training</h4>
            <p className="text-sm text-green-600">Train and deploy custom models</p>
          </div>
        </RoleGate>

        {/* Admin Features */}
        <AdminGate fallback={<div className="p-4 bg-gray-100 rounded">Admin only</div>}>
          <div className="p-4 bg-red-50 rounded">
            <h4 className="font-medium text-red-800">Admin Panel</h4>
            <p className="text-sm text-red-600">System administration</p>
          </div>
        </AdminGate>
      </div>

      {/* Conditional Rendering with Access Control */}
      <AccessControlled
        permissions={['admin:users', 'admin:system']}
        requireAll={false}
        fallback={
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
            <p className="text-yellow-800">
              🔒 This section requires administrative privileges
            </p>
          </div>
        }
        debug={true} // Enable debug logging
      >
        <div className="p-4 bg-red-50 border border-red-200 rounded">
          <h4 className="font-medium text-red-800">System Administration</h4>
          <p className="text-sm text-red-600 mb-3">
            Danger zone - these actions affect the entire system
          </p>
          <div className="flex gap-2">
            <SecureButton
              permission="admin:system"
              variant="destructive"
              size="sm"
              disabledMessage="System admin required"
            >
              Reset Database
            </SecureButton>
            <SecureButton
              permission="admin:users"
              variant="destructive"
              size="sm"
              disabledMessage="User admin required"
            >
              Manage Users
            </SecureButton>
          </div>
        </div>
      </AccessControlled>
    </div>
  );
};

/**
 * Usage Guide Component
 */
export const PermissionSystemGuide: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold mb-4">Permission-Aware UI System</h1>
        <p className="text-gray-600">
          This system ensures that UI elements are only shown when users have the proper permissions.
          No more confusing "Access Denied" messages - buttons simply don't appear if the user can't use them.
        </p>
      </div>

      <div className="space-y-6">
        <h2 className="text-xl font-semibold">Component Examples</h2>
        
        {/* Role Indicators */}
        <div className="p-4 bg-blue-50 rounded-lg">
          <h3 className="font-medium mb-2">Current User Capabilities:</h3>
          <div className="flex gap-2 flex-wrap">
            <RoleGate role="admin">
              <span className="px-2 py-1 bg-red-100 text-red-800 rounded text-xs">Admin</span>
            </RoleGate>
            <RoleGate role="premium_user">
              <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs">Premium</span>
            </RoleGate>
            <RoleGate role="ai_user">
              <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">AI User</span>
            </RoleGate>
            <RoleGate role="ml_engineer">
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">ML Engineer</span>
            </RoleGate>
            <RoleGate role="basic_user">
              <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs">Basic User</span>
            </RoleGate>
            <RoleGate role="viewer">
              <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">Viewer</span>
            </RoleGate>
          </div>
        </div>

        <ExampleAssetCard 
          asset={{
            id: 'asset-123',
            name: 'Example Texture',
            type: 'texture',
            userId: 'user-456'
          }}
          currentUserId="user-789"
        />
        
        <ExampleProjectDashboard />
      </div>

      <div className="p-4 bg-green-50 rounded-lg">
        <h3 className="font-medium text-green-800 mb-2">✅ Benefits of This System</h3>
        <ul className="text-sm text-green-700 space-y-1">
          <li>• UI automatically reflects user permissions</li>
          <li>• No confusing "Access Denied" messages</li>
          <li>• Consistent with backend security model</li>
          <li>• Improved user experience</li>
          <li>• Reduced support requests about unavailable features</li>
          <li>• Clear upgrade paths for premium features</li>
        </ul>
      </div>
    </div>
  );
};