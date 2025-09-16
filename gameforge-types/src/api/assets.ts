/**
 * Asset-related API Types
 */

import { ApiResponse, PaginationParams } from './common';
import { User } from './auth';

export interface Asset {
  id: string;
  name: string;
  type: AssetType;
  category: AssetCategory;
  status: AssetStatus;
  src?: string;
  thumbnail?: string;
  userId: string;
  user?: User;
  projectId?: string;
  tags: string[];
  metadata: AssetMetadata;
  createdAt: string;
  updatedAt: string;
}

export type AssetType = 'image' | 'audio' | 'model' | 'text' | 'code' | 'video';

export type AssetCategory = 
  | 'character' 
  | 'environment' 
  | 'prop' 
  | 'ui' 
  | 'concept'
  | 'music'
  | 'sound-fx'
  | 'voice-lines'
  | 'ambient'
  | 'animation'
  | 'texture'
  | 'script';

export type AssetStatus = 'requested' | 'generating' | 'processing' | 'completed' | 'failed' | 'archived';

export interface AssetMetadata {
  fileSize?: number;
  duration?: number; // for audio/video
  dimensions?: {
    width: number;
    height: number;
  };
  format?: string;
  quality?: 'draft' | 'good' | 'excellent';
  aiGenerated: boolean;
  originalPrompt?: string;
  generationParams?: Record<string, any>;
  usageCount: number;
  collections: string[];
}

export interface CreateAssetRequest {
  name: string;
  type: AssetType;
  category: AssetCategory;
  projectId?: string;
  tags?: string[];
  metadata?: Partial<AssetMetadata>;
}

export interface UpdateAssetRequest {
  name?: string;
  category?: AssetCategory;
  status?: AssetStatus;
  projectId?: string;
  tags?: string[];
  metadata?: Partial<AssetMetadata>;
}

export interface AssetListParams extends PaginationParams {
  type?: AssetType;
  category?: AssetCategory;
  status?: AssetStatus;
  userId?: string;
  projectId?: string;
  search?: string;
  tags?: string[];
}

export interface AssetGenerationRequest {
  prompt: string;
  type: AssetType;
  category: AssetCategory;
  style?: string;
  quality?: 'draft' | 'good' | 'excellent';
  dimensions?: {
    width: number;
    height: number;
  };
  duration?: number; // for audio
  format?: string;
  seed?: number;
  projectId?: string;
  tags?: string[];
}

export interface AssetCollection {
  id: string;
  name: string;
  description?: string;
  assetIds: string[];
  userId: string;
  isPublic: boolean;
  createdAt: string;
  updatedAt: string;
}

// API Response types
export type AssetResponse = ApiResponse<Asset>;
export type AssetListResponse = ApiResponse<Asset[]>;
export type AssetCollectionResponse = ApiResponse<AssetCollection>;