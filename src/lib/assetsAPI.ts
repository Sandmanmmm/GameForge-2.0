/**
 * Assets API client for communicating with backend asset management endpoints.
 */
import { gameforgeAPI } from '../services/api';

// Re-use the auth token utility from aiAPI
function getAuthToken(): string | null {
  const token = localStorage.getItem('token');
  return token;
}

// Asset API response types
export interface AssetMetadata {
  id: string;
  name: string;
  category: string;
  style: string;
  status: string;
  created_at: string;
  file_size?: number;
  dimensions?: string;
  tags: string[];
}

export interface AssetResponse {
  id: string;
  name: string;
  category: string;
  style: string;
  status: string;
  asset_url: string;
  thumbnail_url?: string;
  metadata: AssetMetadata;
}

// Base API call function for assets - now uses centralized API service
async function assetApiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  try {
    const method = (options.method || 'GET') as 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
    let response;
    
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
    
    if (response.success && response.data) {
      return response.data;
    } else {
      throw new Error(response.error?.message || 'API request failed');
    }
  } catch (error) {
    console.error(`Asset API call failed for ${endpoint}:`, error);
    throw error;
  }
}

// Asset API functions
export async function getUserAssets(
  category?: string,
  style?: string,
  status?: string,
  limit: number = 50,
  offset: number = 0
): Promise<AssetResponse[]> {
  const params = new URLSearchParams();
  if (category) params.append('category', category);
  if (style) params.append('style', style);
  if (status) params.append('status', status);
  if (limit) params.append('limit', limit.toString());
  if (offset) params.append('offset', offset.toString());
  
  const queryString = params.toString() ? `?${params.toString()}` : '';
  
  return assetApiCall<AssetResponse[]>(`/assets${queryString}`);
}

export async function getAsset(assetId: string): Promise<AssetResponse> {
  return assetApiCall<AssetResponse>(`/assets/${assetId}`);
}

export async function deleteAsset(assetId: string): Promise<{ message: string }> {
  return assetApiCall<{ message: string }>(`/assets/${assetId}`, {
    method: 'DELETE',
  });
}

export async function updateAssetMetadata(
  assetId: string, 
  metadata: AssetMetadata
): Promise<{ message: string }> {
  return assetApiCall<{ message: string }>(`/assets/${assetId}/metadata`, {
    method: 'PATCH',
    body: JSON.stringify(metadata),
  });
}