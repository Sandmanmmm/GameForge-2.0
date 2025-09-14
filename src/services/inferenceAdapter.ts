/**
 * Inference Service Adapter for GameForge UI Components
 * 
 * This adapter provides compatibility between the new secure inference service
 * and the existing UI components, enabling gradual migration.
 */

import { 
  inferenceClient, 
  InferenceRequest, 
  DiffusionRequest, 
  AudioGenerationRequest,
  InferenceJob 
} from '../services/inference';

// Legacy interfaces to maintain compatibility with existing components
export interface LegacyAssetGenerationRequest {
  prompt: string;
  assetType?: string;
  style?: string;
  size?: string;
  count?: number;
  provider?: 'huggingface' | 'replicate' | 'local' | 'inference';
  quality?: 'draft' | 'standard' | 'high' | 'ultra';
  negative_prompt?: string;
  seed?: number;
}

export interface LegacyAssetGenerationResponse {
  assets?: Array<{
    id: string;
    filename?: string;
    path?: string;
    url: string;
    type?: string;
    style?: string;
    size?: string;
  }>;
  jobId?: string;
  status?: 'processing' | 'completed' | 'failed';
  message?: string;
  trackingUrl?: string;
  provider?: string;
  estimatedTime?: string;
  metadata?: {
    prompt: string;
    assetType?: string;
    style?: string;
    size?: string;
    provider: string;
    generatedAt: string;
  };
}

export interface LegacyTextGenerationRequest {
  prompt: string;
  language?: string;
  framework?: string;
  gameType?: string;
  complexity?: 'simple' | 'medium' | 'complex';
  provider?: 'huggingface' | 'replicate' | 'local' | 'inference';
  maxTokens?: number;
  temperature?: number;
}

export interface LegacyTextGenerationResponse {
  id: string;
  text: string;
  metadata: {
    prompt: string;
    provider: string;
    generatedAt: string;
  };
}

/**
 * Adapter class that bridges the new inference service with legacy UI expectations
 */
export class InferenceServiceAdapter {
  private static instance: InferenceServiceAdapter;
  
  public static getInstance(): InferenceServiceAdapter {
    if (!InferenceServiceAdapter.instance) {
      InferenceServiceAdapter.instance = new InferenceServiceAdapter();
    }
    return InferenceServiceAdapter.instance;
  }

  /**
   * Generate assets using the new inference service while maintaining legacy interface
   */
  async generateAssets(request: LegacyAssetGenerationRequest): Promise<LegacyAssetGenerationResponse> {
    // If explicitly requesting inference provider or auto-selecting best option
    if (request.provider === 'inference' || !request.provider || request.provider === 'local') {
      return this.generateAssetsWithInferenceService(request);
    }
    
    // Fallback to original aiAPI for other providers
    const { generateAssets } = await import('../lib/aiAPI');
    const result = await generateAssets({
      prompt: request.prompt,
      assetType: request.assetType,
      style: request.style,
      size: request.size,
      count: request.count,
      provider: request.provider,
    });
    
    // Handle the APIResponse wrapper structure
    if (result && typeof result === 'object' && 'data' in result) {
      return result.data as LegacyAssetGenerationResponse;
    }
    
    return result as LegacyAssetGenerationResponse;
  }

  /**
   * Generate text using the new inference service
   */
  async generateText(request: LegacyTextGenerationRequest): Promise<LegacyTextGenerationResponse> {
    if (request.provider === 'inference' || !request.provider || request.provider === 'local') {
      return this.generateTextWithInferenceService(request);
    }
    
    // Fallback to original aiAPI for other providers
    const { generateStory } = await import('../lib/aiAPI');
    const result = await generateStory({
      prompt: request.prompt,
      gameType: request.gameType,
      provider: request.provider,
    });
    
    // Handle the APIResponse wrapper structure
    if (result && typeof result === 'object' && 'data' in result && result.data) {
      return {
        id: result.data.id,
        text: result.data.story,
        metadata: {
          prompt: request.prompt,
          provider: request.provider || 'unknown',
          generatedAt: new Date().toISOString(),
        },
      };
    }
    
    // Handle direct response structure
    if (result && typeof result === 'object' && 'id' in result && 'story' in result) {
      return {
        id: (result as any).id,
        text: (result as any).story,
        metadata: {
          prompt: request.prompt,
          provider: request.provider || 'unknown',
          generatedAt: new Date().toISOString(),
        },
      };
    }
    
    throw new Error('Unexpected response format from text generation API');
  }

  /**
   * Poll job until completion (compatible with existing UI)
   */
  async pollJobUntilComplete(
    jobId: string,
    onProgress?: (progress: { 
      status: string; 
      progress?: number; 
      message?: string; 
      estimatedTime?: string 
    }) => void
  ): Promise<any> {
    return inferenceClient.pollJobUntilComplete(jobId, (job) => {
      if (onProgress) {
        onProgress({
          status: job.status,
          progress: job.progress,
          message: this.getStatusMessage(job),
          estimatedTime: this.estimateTimeRemaining(job),
        });
      }
    });
  }

  /**
   * Private method to handle inference service asset generation
   */
  private async generateAssetsWithInferenceService(
    request: LegacyAssetGenerationRequest
  ): Promise<LegacyAssetGenerationResponse> {
    try {
      // Parse size for dimensions
      const [width, height] = this.parseImageSize(request.size || '1024x1024');
      
      // Map quality to inference steps
      const steps = this.mapQualityToSteps(request.quality || 'standard');
      
      // Determine model based on asset type or style
      const model = this.selectImageModel(request.assetType, request.style);
      
      const inferenceRequest: DiffusionRequest = {
        model,
        prompt: request.prompt,
        negative_prompt: request.negative_prompt,
        width,
        height,
        num_inference_steps: steps,
        guidance_scale: 7.5,
        num_images: request.count || 1,
        seed: request.seed,
        metadata: {
          assetType: request.assetType,
          style: request.style,
          originalRequest: request,
        },
      };

      const job = await inferenceClient.generateImage(inferenceRequest);
      
      return {
        jobId: job.job_id,
        status: 'processing',
        message: 'Asset generation started',
        provider: 'inference',
        estimatedTime: this.estimateGenerationTime(request),
        metadata: {
          prompt: request.prompt,
          assetType: request.assetType,
          style: request.style,
          size: request.size,
          provider: 'inference',
          generatedAt: new Date().toISOString(),
        },
      };
    } catch (error) {
      console.error('Inference service generation failed:', error);
      return {
        status: 'failed',
        message: error instanceof Error ? error.message : 'Generation failed',
        provider: 'inference',
        metadata: {
          prompt: request.prompt,
          provider: 'inference',
          generatedAt: new Date().toISOString(),
        },
      };
    }
  }

  /**
   * Private method to handle inference service text generation
   */
  private async generateTextWithInferenceService(
    request: LegacyTextGenerationRequest
  ): Promise<LegacyTextGenerationResponse> {
    try {
      // Determine model based on context
      const model = this.selectTextModel(request.gameType, request.framework);
      
      const inferenceRequest: InferenceRequest = {
        model,
        prompt: request.prompt,
        max_tokens: request.maxTokens || 512,
        temperature: request.temperature || 0.7,
        top_p: 0.9,
        metadata: {
          gameType: request.gameType,
          framework: request.framework,
          complexity: request.complexity,
        },
      };

      const job = await inferenceClient.generateText(inferenceRequest);
      const result = await inferenceClient.pollJobUntilComplete(job.job_id);
      
      if (result.status === 'completed' && result.result) {
        return {
          id: job.job_id,
          text: result.result.text || result.result.content || '',
          metadata: {
            prompt: request.prompt,
            provider: 'inference',
            generatedAt: new Date().toISOString(),
          },
        };
      } else {
        throw new Error(result.error || 'Text generation failed');
      }
    } catch (error) {
      console.error('Inference service text generation failed:', error);
      throw error;
    }
  }

  /**
   * Utility methods for mapping and configuration
   */
  private parseImageSize(size: string): [number, number] {
    const parts = size.split('x');
    return [parseInt(parts[0]) || 1024, parseInt(parts[1]) || 1024];
  }

  private mapQualityToSteps(quality: string): number {
    switch (quality) {
      case 'draft': return 10;
      case 'standard': return 20;
      case 'high': return 30;
      case 'ultra': return 50;
      default: return 20;
    }
  }

  private selectImageModel(assetType?: string, style?: string): string {
    // Model selection logic based on asset type and style
    if (assetType?.includes('character') || style?.includes('portrait')) {
      return 'sdxl-base'; // Good for characters
    }
    if (assetType?.includes('environment') || style?.includes('landscape')) {
      return 'sdxl-base'; // Good for environments
    }
    return 'sdxl-base'; // Default stable diffusion model
  }

  private selectTextModel(gameType?: string, framework?: string): string {
    // Model selection logic based on context
    if (gameType?.includes('RPG') || gameType?.includes('story')) {
      return 'llama2-7b-chat'; // Good for narrative
    }
    if (framework?.includes('code') || framework?.includes('programming')) {
      return 'llama2-7b-chat'; // Can handle code generation
    }
    return 'llama2-7b-chat'; // Default language model
  }

  private estimateGenerationTime(request: LegacyAssetGenerationRequest): string {
    const baseTime = 30; // seconds
    const qualityMultiplier = request.quality === 'ultra' ? 2 : 
                             request.quality === 'high' ? 1.5 : 1;
    const countMultiplier = request.count || 1;
    
    const estimatedSeconds = baseTime * qualityMultiplier * countMultiplier;
    return `${Math.ceil(estimatedSeconds / 60)} minutes`;
  }

  private getStatusMessage(job: InferenceJob): string {
    switch (job.status) {
      case 'pending': return 'Queued for processing...';
      case 'running': return `Generating... ${job.progress ? Math.round(job.progress * 100) : 0}%`;
      case 'completed': return 'Generation completed!';
      case 'failed': return `Failed: ${job.error || 'Unknown error'}`;
      case 'cancelled': return 'Generation cancelled';
      default: return 'Processing...';
    }
  }

  private estimateTimeRemaining(job: InferenceJob): string {
    if (job.progress && job.progress > 0 && job.started_at) {
      const elapsed = Date.now() - new Date(job.started_at).getTime();
      const total = elapsed / job.progress;
      const remaining = total - elapsed;
      return `${Math.ceil(remaining / 1000)} seconds`;
    }
    return '~30 seconds';
  }
}

// Export singleton instance for convenience
export const inferenceAdapter = InferenceServiceAdapter.getInstance();

// Provide drop-in replacements for existing API functions
export async function generateAssets(request: LegacyAssetGenerationRequest): Promise<LegacyAssetGenerationResponse> {
  return inferenceAdapter.generateAssets(request);
}

export async function generateText(request: LegacyTextGenerationRequest): Promise<LegacyTextGenerationResponse> {
  return inferenceAdapter.generateText(request);
}

export async function pollJobUntilComplete(
  jobId: string,
  onProgress?: (progress: any) => void
): Promise<any> {
  return inferenceAdapter.pollJobUntilComplete(jobId, onProgress);
}

// Health check and status functions
export async function getInferenceServiceStatus() {
  try {
    const health = await inferenceClient.healthCheck();
    const stats = await inferenceClient.getStats();
    return {
      available: true,
      status: health.status,
      stats,
      timestamp: health.timestamp,
    };
  } catch (error) {
    return {
      available: false,
      status: 'unavailable',
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString(),
    };
  }
}

export async function getAvailableModels() {
  try {
    return await inferenceClient.getModels();
  } catch (error) {
    console.error('Failed to get available models:', error);
    return [];
  }
}