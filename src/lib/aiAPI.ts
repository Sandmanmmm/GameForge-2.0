// AI API Client for GameForge Frontend
import { gameforgeAPI } from '../services/api';

interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    message: string;
    details?: string;
  };
}

// AI Generation Request Types
export interface StoryGenerationRequest {
  prompt: string;
  gameType?: string;
  genre?: string;
  tone?: string;
  length?: 'short' | 'medium' | 'long';
  context?: string;
  provider?: 'huggingface' | 'replicate' | 'local';
}

export interface AssetGenerationRequest {
  prompt: string;
  assetType?: string;
  style?: string;
  size?: string;
  count?: number;
  provider?: 'huggingface' | 'replicate' | 'local';
}

// New AI Generation Request Types (Job-based API)
export interface AIGenerateRequest {
  prompt: string;
  style?: string;
  category?: string;
  width?: number;
  height?: number;
  quality?: 'draft' | 'standard' | 'high' | 'ultra';
  count?: number;
  negative_prompt?: string;
  seed?: number;
  model?: string;
}

export interface SuperResRequest {
  scale_factor?: number;
  enhance_details?: boolean;
  preserve_style?: boolean;
  noise_reduction?: number;
  model?: string;
}

export interface CodeGenerationRequest {
  prompt: string;
  language?: string;
  framework?: string;
  gameType?: string;
  complexity?: 'simple' | 'medium' | 'complex';
  provider?: 'huggingface' | 'replicate' | 'local';
}

// Response Types
export interface StoryGenerationResponse {
  id: string;
  story: string;
  metadata: {
    prompt: string;
    gameType?: string;
    genre?: string;
    tone?: string;
    length?: string;
    provider: string;
    generatedAt: string;
  };
}

export interface AssetGenerationResponse {
  // Direct response (fallback providers)
  assets?: Array<{
    id: string;
    filename?: string;
    path?: string;
    url: string;
    type?: string;
    style?: string;
    size?: string;
  }>;
  // Job-based response (SDXL service)
  jobId?: string;
  status?: 'processing' | 'completed' | 'failed';
  message?: string;
  trackingUrl?: string;
  provider?: string;
  estimatedTime?: string;
  // Metadata for both types
  metadata?: {
    prompt: string;
    assetType?: string;
    style?: string;
    size?: string;
    count?: number;
    provider: string;
    generatedAt: string;
  };
}

// New AI Generation Response Types (Job-based API)
export interface AIGenerateResponse {
  job_id: string;
  status: string;
  message: string;
  estimated_duration?: number;
  tracking_url: string;
}

export interface JobMetadata {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  asset_url?: string;
  created_at: string;
  updated_at: string;
  estimated_completion?: string;
  error_message?: string;
  metadata: Record<string, any>;
}

export interface JobStatusResponse {
  success: boolean;
  data: JobMetadata;
}

export interface CodeGenerationResponse {
  id: string;
  code: string;
  metadata: {
    prompt: string;
    language?: string;
    framework?: string;
    gameType?: string;
    complexity?: string;
    provider: string;
    generatedAt: string;
  };
}

// Utility function to get auth token
function getAuthToken(): string | null {
  const token = localStorage.getItem('token');
  return token;
}

// Base API call function - now uses centralized API service
async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<APIResponse<T>> {
  try {
    const method = (options.method || 'GET') as 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
    let response: APIResponse<T>;
    
    if (method === 'GET') {
      response = await gameforgeAPI.get<T>(endpoint);
    } else if (method === 'POST') {
      const body = options.body ? (options.body instanceof FormData ? options.body : JSON.parse(options.body as string)) : undefined;
      response = await gameforgeAPI.post<T>(endpoint, body);
    } else if (method === 'PUT') {
      const body = options.body ? (options.body instanceof FormData ? options.body : JSON.parse(options.body as string)) : undefined;
      response = await gameforgeAPI.put<T>(endpoint, body);
    } else if (method === 'DELETE') {
      response = await gameforgeAPI.delete<T>(endpoint);
    } else if (method === 'PATCH') {
      const body = options.body ? (options.body instanceof FormData ? options.body : JSON.parse(options.body as string)) : undefined;
      response = await gameforgeAPI.patch<T>(endpoint, body);
    } else {
      throw new Error(`Unsupported HTTP method: ${method}`);
    }
    
    return response;
  } catch (error) {
    console.error(`API call failed for ${endpoint}:`, error);
    return {
      success: false,
      error: {
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      },
    };
  }
}

// AI API Functions

export async function generateStory(
  request: StoryGenerationRequest
): Promise<APIResponse<StoryGenerationResponse>> {
  return apiCall<StoryGenerationResponse>('/ai/story', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function generateAssets(
  request: AssetGenerationRequest
): Promise<APIResponse<AssetGenerationResponse>> {
  return apiCall<AssetGenerationResponse>('/ai/assets', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// New AI Generation Functions (Job-based API)
export async function generateAIAsset(
  request: AIGenerateRequest
): Promise<APIResponse<AIGenerateResponse>> {
  return apiCall<AIGenerateResponse>('/ai/generate', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getJobStatus(
  jobId: string
): Promise<APIResponse<JobStatusResponse>> {
  return apiCall<JobStatusResponse>(`/ai/job/${jobId}`, {
    method: 'GET',
  });
}

export async function superResolution(
  request: SuperResRequest,
  file: File
): Promise<APIResponse<AIGenerateResponse>> {
  const formData = new FormData();
  formData.append('file', file);
  
  // Append request parameters
  Object.entries(request).forEach(([key, value]) => {
    if (value !== undefined) {
      formData.append(key, value.toString());
    }
  });

  return apiCall<AIGenerateResponse>('/ai/superres', {
    method: 'POST',
    body: formData,
    headers: {}, // Don't set Content-Type for FormData
  });
}

export async function cancelJob(
  jobId: string
): Promise<APIResponse<{ message: string }>> {
  return apiCall<{ message: string }>(`/ai/job/${jobId}`, {
    method: 'DELETE',
  });
}

export async function listJobs(
  status?: string,
  limit?: number,
  offset?: number
): Promise<APIResponse<JobMetadata[]>> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (limit) params.append('limit', limit.toString());
  if (offset) params.append('offset', offset.toString());
  
  const queryString = params.toString() ? `?${params.toString()}` : '';
  
  return apiCall<JobMetadata[]>(`/ai/jobs${queryString}`, {
    method: 'GET',
  });
}

// Job polling utility
export async function pollJobUntilComplete(
  jobId: string,
  onProgress?: (job: JobMetadata) => void,
  intervalMs: number = 2000,
  timeoutMs: number = 300000 // 5 minutes
): Promise<JobMetadata> {
  const startTime = Date.now();
  
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        if (Date.now() - startTime > timeoutMs) {
          reject(new Error('Job polling timeout'));
          return;
        }
        
        const response = await getJobStatus(jobId);
        
        if (!response.success || !response.data) {
          reject(new Error(response.error?.message || 'Failed to get job status'));
          return;
        }
        
        const job = response.data.data;
        onProgress?.(job);
        
        if (job.status === 'completed') {
          resolve(job);
        } else if (job.status === 'failed' || job.status === 'cancelled') {
          reject(new Error(job.error_message || `Job ${job.status}`));
        } else {
          // Continue polling
          setTimeout(poll, intervalMs);
        }
      } catch (error) {
        reject(error);
      }
    };
    
    poll();
  });
}

export async function generateCode(
  request: CodeGenerationRequest
): Promise<APIResponse<CodeGenerationResponse>> {
  return apiCall<CodeGenerationResponse>('/ai/code', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// Utility functions for AI providers
export const AI_PROVIDERS = {
  HUGGINGFACE: 'huggingface',
  REPLICATE: 'replicate',
  LOCAL: 'local',
} as const;

export const STORY_GENRES = [
  'fantasy',
  'sci-fi',
  'horror',
  'adventure',
  'mystery',
  'romance',
  'comedy',
  'drama',
  'action',
  'thriller',
] as const;

export const STORY_TONES = [
  'heroic',
  'dark',
  'comedic',
  'mysterious',
  'epic',
  'intimate',
  'adventurous',
  'melancholic',
  'whimsical',
  'serious',
] as const;

export const ASSET_TYPES = [
  'concept art',
  'character design',
  'environment art',
  'prop design',
  'ui element',
  'icon',
  'texture',
  'sprite',
  'background',
  'logo',
] as const;

export const ART_STYLES = [
  'fantasy digital art',
  'pixel art',
  'cartoon style',
  'realistic 3D',
  'anime style',
  'minimalist',
  'gothic',
  'cyberpunk',
  'steampunk',
  'watercolor',
] as const;

export const PROGRAMMING_LANGUAGES = [
  'javascript',
  'typescript',
  'python',
  'csharp',
  'cpp',
  'java',
  'rust',
  'go',
  'lua',
  'gdscript',
] as const;

export const GAME_FRAMEWORKS = [
  'unity',
  'unreal',
  'godot',
  'phaser',
  'three.js',
  'react',
  'vue',
  'pygame',
  'love2d',
  'defold',
] as const;
