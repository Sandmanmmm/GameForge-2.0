/**
 * GameForge Inference Service API Client
 * 
 * Frontend client for the secure inference microservice.
 * Handles authentication, job management, status polling, and error handling.
 */

import { useState, useEffect, useCallback } from 'react';
import { inferenceAPI } from './api';

// Polling configuration
const POLLING_INTERVAL = 1000; // 1 second
const MAX_POLL_ATTEMPTS = 300; // 5 minutes max

// Type definitions matching the backend inference service
export interface InferenceRequest {
  model: string;
  prompt: string;
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  top_k?: number;
  repetition_penalty?: number;
  seed?: number;
  lora_adapters?: LoRAAdapter[];
  metadata?: Record<string, any>;
}

export interface LoRAAdapter {
  name: string;
  weight?: number;
  uri?: string;
  sha256?: string;
}

export interface DiffusionRequest {
  model: string;
  prompt: string;
  negative_prompt?: string;
  width?: number;
  height?: number;
  num_inference_steps?: number;
  guidance_scale?: number;
  num_images?: number;
  seed?: number;
  lora_adapters?: LoRAAdapter[];
  metadata?: Record<string, any>;
}

export interface AudioGenerationRequest {
  model: string;
  prompt: string;
  duration?: number;
  temperature?: number;
  top_k?: number;
  top_p?: number;
  seed?: number;
  lora_adapters?: LoRAAdapter[];
  metadata?: Record<string, any>;
}

export interface InferenceJob {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  model: string;
  request_type: 'text' | 'image' | 'audio';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  progress?: number;
  result?: any;
  error?: string;
  metadata?: Record<string, any>;
}

export interface ModelInfo {
  name: string;
  type: 'text' | 'image' | 'audio';
  status: 'available' | 'loading' | 'unavailable';
  description?: string;
  license?: string;
  parameters?: Record<string, any>;
  lora_adapters?: string[];
}

export interface InferenceStats {
  total_jobs: number;
  active_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  success_rate: number;
  avg_completion_time: number;
  models_loaded: number;
  system_health: 'healthy' | 'degraded' | 'critical';
}

export interface APIError {
  message: string;
  code: string;
  details?: any;
}

export class InferenceAPIError extends Error {
  constructor(
    message: string, 
    public code: string, 
    public status: number,
    public details?: any
  ) {
    super(message);
    this.name = 'InferenceAPIError';
  }
}

/**
 * GameForge Inference Service Client
 */
export class InferenceClient {
  private apiKey: string | null = null;
  private authToken: string | null = null;

  constructor() {
    // No need for baseURL since we use centralized API client
  }

  /**
   * Set authentication credentials
   */
  setAuth(apiKey?: string, authToken?: string) {
    this.apiKey = apiKey || null;
    this.authToken = authToken || null;
  }

  /**
   * Get authentication headers
   */
  private getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    return headers;
  }

  /**
   * Make authenticated API request using centralized API client
   */
  private async makeRequest<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    try {
      const method = (options.method || 'GET') as 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
      let response;
      
      if (method === 'GET') {
        response = await inferenceAPI.get<T>(endpoint);
      } else if (method === 'POST') {
        const body = options.body ? (options.body instanceof FormData ? options.body : JSON.parse(options.body as string)) : undefined;
        response = await inferenceAPI.post<T>(endpoint, body);
      } else if (method === 'PUT') {
        const body = options.body ? (options.body instanceof FormData ? options.body : JSON.parse(options.body as string)) : undefined;
        response = await inferenceAPI.put<T>(endpoint, body);
      } else if (method === 'DELETE') {
        response = await inferenceAPI.delete<T>(endpoint);
      } else if (method === 'PATCH') {
        const body = options.body ? (options.body instanceof FormData ? options.body : JSON.parse(options.body as string)) : undefined;
        response = await inferenceAPI.patch<T>(endpoint, body);
      } else {
        throw new Error(`Unsupported HTTP method: ${method}`);
      }

      if (response.success && response.data) {
        return response.data;
      } else {
        throw new InferenceAPIError(
          response.error?.message || 'API request failed',
          'API_ERROR',
          500,
          response.error
        );
      }
    } catch (error) {
      if (error instanceof InferenceAPIError) {
        throw error;
      }
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new InferenceAPIError(
        `Network error: ${errorMessage}`,
        'NETWORK_ERROR',
        0,
        error
      );
    }
  }

  /**
   * Get available models
   */
  async getModels(): Promise<ModelInfo[]> {
    return this.makeRequest<ModelInfo[]>('/models');
  }

  /**
   * Get specific model info
   */
  async getModel(modelName: string): Promise<ModelInfo> {
    return this.makeRequest<ModelInfo>(`/models/${modelName}`);
  }

  /**
   * Load a model
   */
  async loadModel(modelName: string): Promise<void> {
    await this.makeRequest(`/models/${modelName}/load`, {
      method: 'POST',
    });
  }

  /**
   * Unload a model
   */
  async unloadModel(modelName: string): Promise<void> {
    await this.makeRequest(`/models/${modelName}/unload`, {
      method: 'POST',
    });
  }

  /**
   * Submit text generation job
   */
  async generateText(request: InferenceRequest): Promise<InferenceJob> {
    return this.makeRequest<InferenceJob>('/inference/text', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Submit image generation job
   */
  async generateImage(request: DiffusionRequest): Promise<InferenceJob> {
    return this.makeRequest<InferenceJob>('/inference/image', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Submit audio generation job
   */
  async generateAudio(request: AudioGenerationRequest): Promise<InferenceJob> {
    return this.makeRequest<InferenceJob>('/inference/audio', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Get job status
   */
  async getJob(jobId: string): Promise<InferenceJob> {
    return this.makeRequest<InferenceJob>(`/jobs/${jobId}`);
  }

  /**
   * Cancel a job
   */
  async cancelJob(jobId: string): Promise<void> {
    await this.makeRequest(`/jobs/${jobId}/cancel`, {
      method: 'POST',
    });
  }

  /**
   * Get all jobs
   */
  async getJobs(limit: number = 50, offset: number = 0): Promise<InferenceJob[]> {
    return this.makeRequest<InferenceJob[]>(`/jobs?limit=${limit}&offset=${offset}`);
  }

  /**
   * Poll job until completion
   */
  async pollJobUntilComplete(
    jobId: string,
    onProgress?: (job: InferenceJob) => void
  ): Promise<InferenceJob> {
    let attempts = 0;
    
    while (attempts < MAX_POLL_ATTEMPTS) {
      const job = await this.getJob(jobId);
      
      if (onProgress) {
        onProgress(job);
      }

      if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
        return job;
      }

      await new Promise(resolve => setTimeout(resolve, POLLING_INTERVAL));
      attempts++;
    }

    throw new InferenceAPIError(
      'Job polling timeout',
      'POLLING_TIMEOUT',
      0,
      { jobId, attempts }
    );
  }

  /**
   * Get inference service statistics
   */
  async getStats(): Promise<InferenceStats> {
    return this.makeRequest<InferenceStats>('/stats');
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.makeRequest<{ status: string; timestamp: string }>('/health');
  }
}

/**
 * React hook for inference service integration
 */
export function useInferenceClient() {
  const client = new InferenceClient();
  
  // Auto-configure auth from context if available
  // TODO: Integrate with existing auth context
  // useEffect(() => {
  //   const authContext = useContext(AuthContext);
  //   if (authContext?.apiKey || authContext?.token) {
  //     client.setAuth(authContext.apiKey, authContext.token);
  //   }
  // }, []);

  return client;
}

// Export singleton instance for convenience
export const inferenceClient = new InferenceClient();