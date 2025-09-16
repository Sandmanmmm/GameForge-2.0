/**
 * Project-related API Types
 */

import { ApiResponse, PaginationParams } from './common';
import { User } from './auth';

export interface GameProject {
  id: string;
  title: string;
  description: string;
  prompt: string;
  status: ProjectStatus;
  progress: number;
  createdAt: string;
  updatedAt: string;
  userId: string;
  user?: User;
  thumbnail?: string;
  isPublic: boolean;
  tags: string[];
  metadata: ProjectMetadata;
}

export type ProjectStatus = 'concept' | 'development' | 'testing' | 'complete' | 'archived';

export interface ProjectMetadata {
  genre?: string;
  targetPlatform?: string[];
  estimatedDuration?: number;
  complexity: 'simple' | 'medium' | 'complex';
  version: string;
  lastModifiedBy?: string;
}

export interface CreateProjectRequest {
  title: string;
  description: string;
  prompt: string;
  isPublic?: boolean;
  tags?: string[];
  metadata?: Partial<ProjectMetadata>;
}

export interface UpdateProjectRequest {
  title?: string;
  description?: string;
  prompt?: string;
  status?: ProjectStatus;
  progress?: number;
  isPublic?: boolean;
  tags?: string[];
  metadata?: Partial<ProjectMetadata>;
}

export interface ProjectListParams extends PaginationParams {
  status?: ProjectStatus;
  userId?: string;
  isPublic?: boolean;
  search?: string;
  tags?: string[];
}

export interface ProjectShareRequest {
  userIds: string[];
  permissions: ProjectPermission[];
  expiresAt?: string;
}

export type ProjectPermission = 'view' | 'edit' | 'manage';

export interface ProjectShare {
  id: string;
  projectId: string;
  sharedWithUserId: string;
  sharedByUserId: string;
  permissions: ProjectPermission[];
  createdAt: string;
  expiresAt?: string;
  isActive: boolean;
}

// API Response types
export type ProjectResponse = ApiResponse<GameProject>;
export type ProjectListResponse = ApiResponse<GameProject[]>;
export type ProjectShareResponse = ApiResponse<ProjectShare>;