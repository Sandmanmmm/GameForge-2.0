/**
 * AI Model-related API Types
 */

import { ApiResponse, PaginationParams } from './common';
import { User } from './auth';

export interface AIModel {
  id: string;
  name: string;
  type: ModelType;
  category: ModelCategory;
  status: ModelStatus;
  userId: string;
  user?: User;
  description?: string;
  version: string;
  config: ModelConfig;
  metrics?: ModelMetrics;
  createdAt: string;
  updatedAt: string;
  lastTrainedAt?: string;
}

export type ModelType = 
  | 'text-to-image'
  | 'text-to-audio' 
  | 'text-to-3d'
  | 'image-enhancement'
  | 'style-transfer'
  | 'custom';

export type ModelCategory = 
  | 'art-generation'
  | 'audio-synthesis'
  | '3d-modeling'
  | 'image-processing'
  | 'game-content'
  | 'utility';

export type ModelStatus = 
  | 'created'
  | 'training'
  | 'trained'
  | 'deployed'
  | 'failed'
  | 'archived';

export interface ModelConfig {
  framework: string;
  architecture: string;
  hyperparameters: Record<string, any>;
  trainingData?: {
    datasetId: string;
    size: number;
    format: string;
  };
  deployment?: {
    endpoint?: string;
    resources: {
      gpu: string;
      memory: string;
      storage: string;
    };
  };
}

export interface ModelMetrics {
  accuracy?: number;
  loss?: number;
  trainingTime?: number; // in seconds
  inferenceTime?: number; // in ms
  modelSize?: number; // in MB
  throughput?: number; // requests per second
}

export interface CreateModelRequest {
  name: string;
  type: ModelType;
  category: ModelCategory;
  description?: string;
  config: Partial<ModelConfig>;
}

export interface UpdateModelRequest {
  name?: string;
  description?: string;
  status?: ModelStatus;
  config?: Partial<ModelConfig>;
}

export interface TrainModelRequest {
  modelId: string;
  datasetId?: string;
  config?: {
    epochs?: number;
    batchSize?: number;
    learningRate?: number;
    [key: string]: any;
  };
}

export interface DeployModelRequest {
  modelId: string;
  resources?: {
    gpu?: string;
    memory?: string;
    replicas?: number;
  };
}

export interface ModelInferenceRequest {
  modelId: string;
  input: Record<string, any>;
  parameters?: Record<string, any>;
}

export interface ModelInferenceResponse {
  output: Record<string, any>;
  executionTime: number;
  modelVersion: string;
  requestId: string;
}

export interface ModelListParams extends PaginationParams {
  type?: ModelType;
  category?: ModelCategory;
  status?: ModelStatus;
  userId?: string;
  search?: string;
}

// API Response types
export type ModelResponse = ApiResponse<AIModel>;
export type ModelListResponse = ApiResponse<AIModel[]>;
export type TrainModelResponse = ApiResponse<{ jobId: string }>;
export type DeployModelResponse = ApiResponse<{ endpoint: string }>;
export type InferenceResponse = ApiResponse<ModelInferenceResponse>;