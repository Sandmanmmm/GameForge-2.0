/**
 * Enhanced AIAssetGenerator Integration Patch
 * 
 * This module provides integration between the existing AIAssetGenerator component
 * and the new secure inference service.
 */

// Import the inference adapter for seamless integration
import { 
  generateAssets, 
  pollJobUntilComplete,
  getInferenceServiceStatus 
} from '../services/inferenceAdapter';

/**
 * Enhanced generation function that uses the new inference service
 * while maintaining compatibility with existing UI components
 */
export async function generateAssetWithInferenceService(
  prompt: string,
  options: {
    stylePreset?: any;
    assetType?: string;
    imageSize?: string;
    qualityLevel?: 'draft' | 'standard' | 'high' | 'ultra';
    generateCount?: number;
    onProgress?: (progress: any) => void;
  } = {}
) {
  const {
    stylePreset,
    assetType = 'concept art',
    imageSize = '1024x1024',
    qualityLevel = 'standard',
    generateCount = 1,
    onProgress
  } = options;

  try {
    // Check if inference service is available
    const serviceStatus = await getInferenceServiceStatus();
    const useInferenceService = serviceStatus.available;

    // Prepare the request
    const request = {
      prompt,
      assetType,
      style: stylePreset?.name || 'digital art',
      size: imageSize,
      count: generateCount,
      quality: qualityLevel,
      provider: useInferenceService ? 'inference' as const : 'huggingface' as const,
    };

    if (onProgress) {
      onProgress({
        status: 'starting',
        message: `Using ${useInferenceService ? 'secure inference service' : 'fallback provider'}`,
        progress: 0,
      });
    }

    // Generate using the adapter (handles provider selection automatically)
    const response = await generateAssets(request);

    if (response.jobId) {
      // Job-based response - poll for completion
      if (onProgress) {
        onProgress({
          status: 'processing',
          message: 'Generation started...',
          jobId: response.jobId,
          progress: 0,
        });
      }

      const result = await pollJobUntilComplete(response.jobId, (progressUpdate) => {
        if (onProgress) {
          onProgress({
            status: 'processing',
            message: progressUpdate.message || 'Generating...',
            progress: progressUpdate.progress || 0,
            jobId: response.jobId,
          });
        }
      });

      return {
        success: true,
        assets: result.result ? [result.result] : [],
        jobId: response.jobId,
        provider: request.provider,
        metadata: {
          prompt,
          assetType,
          style: stylePreset?.name,
          generatedAt: new Date().toISOString(),
          inferenceService: useInferenceService,
        },
      };
    } else if (response.assets) {
      // Direct response
      return {
        success: true,
        assets: response.assets,
        provider: request.provider,
        metadata: {
          prompt,
          assetType,
          style: stylePreset?.name,
          generatedAt: new Date().toISOString(),
          inferenceService: useInferenceService,
        },
      };
    } else {
      throw new Error('Unexpected response format');
    }
  } catch (error) {
    console.error('Asset generation failed:', error);
    throw error;
  }
}

/**
 * Service status checker for UI components
 */
export async function checkInferenceServiceHealth() {
  try {
    const status = await getInferenceServiceStatus();
    return {
      available: status.available,
      status: status.status,
      models: status.stats?.models_loaded || 0,
      activeJobs: status.stats?.active_jobs || 0,
      successRate: status.stats?.success_rate || 0,
    };
  } catch (error) {
    return {
      available: false,
      status: 'error',
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Integration instructions for existing components:
 * 
 * 1. Replace the existing generateAIAsset call with generateAssetWithInferenceService
 * 2. The function maintains the same interface but uses the secure inference service when available
 * 3. Fallback to existing providers happens automatically
 * 4. Progress callbacks work the same way
 * 
 * Example usage in AIAssetGenerator.tsx:
 * 
 * ```tsx
 * import { generateAssetWithInferenceService } from './InferenceIntegration';
 * 
 * // Replace this:
 * // const response = await generateAIAsset(aiRequest)
 * 
 * // With this:
 * const response = await generateAssetWithInferenceService(enhancedPrompt, {
 *   stylePreset: selectedStylePreset,
 *   assetType: selectedAssetType,
 *   imageSize,
 *   qualityLevel,
 *   generateCount,
 *   onProgress: (progress) => {
 *     setGenerationProgress(prev => prev ? { ...prev, ...progress } : null);
 *   }
 * });
 * ```
 */

export const INTEGRATION_NOTES = `
🚀 GameForge Inference Service Integration

✅ COMPLETED:
- Secure inference microservice backend (services/inference/)
- Model loading with SHA256 verification
- Runtime LoRA composition
- Frontend API client (src/services/inference.ts)
- Compatibility adapter (src/services/inferenceAdapter.ts)
- React hooks for UI integration

🔄 INTEGRATION STEPS:
1. Update AIAssetGenerator to use generateAssetWithInferenceService
2. Add service status indicator to UI
3. Implement authentication token passing
4. Add error handling for rate limits and auth failures
5. Create observability dashboard

💡 BENEFITS:
- Secure, verified model loading
- Better performance with local inference
- Enhanced security with checksum validation
- Automatic fallback to external providers
- Job tracking and progress monitoring
`;