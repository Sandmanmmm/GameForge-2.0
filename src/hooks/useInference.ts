/**
 * React hooks for GameForge Inference Service
 * 
 * Provides React hooks for easy integration with the inference service
 */

import { useState, useEffect, useCallback } from 'react';
import { 
  InferenceClient, 
  InferenceJob, 
  ModelInfo, 
  InferenceStats, 
  APIError, 
  InferenceAPIError,
  inferenceClient 
} from '../services/inference';

/**
 * Job management hook
 */
export function useInferenceJob(jobId?: string) {
  const [job, setJob] = useState<InferenceJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<APIError | null>(null);
  const client = inferenceClient;

  const pollJob = useCallback(async (id: string) => {
    if (!id) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await client.pollJobUntilComplete(id, (updatedJob) => {
        setJob(updatedJob);
      });
      setJob(result);
    } catch (err) {
      if (err instanceof InferenceAPIError) {
        setError({
          message: err.message,
          code: err.code,
          details: err.details,
        });
      } else {
        setError({
          message: 'Unknown error occurred',
          code: 'UNKNOWN_ERROR',
          details: err,
        });
      }
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    if (jobId) {
      pollJob(jobId);
    }
  }, [jobId, pollJob]);

  return { job, loading, error, pollJob };
}

/**
 * Models management hook
 */
export function useInferenceModels() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<APIError | null>(null);
  const client = inferenceClient;

  const loadModels = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await client.getModels();
      setModels(result);
    } catch (err) {
      if (err instanceof InferenceAPIError) {
        setError({
          message: err.message,
          code: err.code,
          details: err.details,
        });
      } else {
        setError({
          message: 'Failed to load models',
          code: 'LOAD_ERROR',
          details: err,
        });
      }
    } finally {
      setLoading(false);
    }
  }, [client]);

  const loadModel = useCallback(async (modelName: string) => {
    try {
      await client.loadModel(modelName);
      await loadModels(); // Refresh models list
    } catch (err) {
      if (err instanceof InferenceAPIError) {
        setError({
          message: err.message,
          code: err.code,
          details: err.details,
        });
      }
      throw err;
    }
  }, [client, loadModels]);

  const unloadModel = useCallback(async (modelName: string) => {
    try {
      await client.unloadModel(modelName);
      await loadModels(); // Refresh models list
    } catch (err) {
      if (err instanceof InferenceAPIError) {
        setError({
          message: err.message,
          code: err.code,
          details: err.details,
        });
      }
      throw err;
    }
  }, [client, loadModels]);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  return { 
    models, 
    loading, 
    error, 
    loadModels, 
    loadModel, 
    unloadModel 
  };
}

/**
 * Inference statistics hook
 */
export function useInferenceStats(refreshInterval: number = 5000) {
  const [stats, setStats] = useState<InferenceStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<APIError | null>(null);
  const client = inferenceClient;

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await client.getStats();
      setStats(result);
    } catch (err) {
      if (err instanceof InferenceAPIError) {
        setError({
          message: err.message,
          code: err.code,
          details: err.details,
        });
      } else {
        setError({
          message: 'Failed to load stats',
          code: 'STATS_ERROR',
          details: err,
        });
      }
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, refreshInterval);
    return () => clearInterval(interval);
  }, [loadStats, refreshInterval]);

  return { stats, loading, error, loadStats };
}

/**
 * Enhanced generation hook that integrates with existing UI patterns
 */
export function useInferenceGeneration() {
  const [activeJobs, setActiveJobs] = useState<Map<string, InferenceJob>>(new Map());
  const [results, setResults] = useState<Map<string, any>>(new Map());
  const [errors, setErrors] = useState<Map<string, APIError>>(new Map());
  const client = inferenceClient;

  const generateImage = useCallback(async (
    prompt: string,
    options: {
      model?: string;
      width?: number;
      height?: number;
      negativePrompt?: string;
      steps?: number;
      guidance?: number;
      seed?: number;
    } = {}
  ) => {
    try {
      const job = await client.generateImage({
        model: options.model || 'sdxl-base',
        prompt,
        negative_prompt: options.negativePrompt,
        width: options.width || 1024,
        height: options.height || 1024,
        num_inference_steps: options.steps || 20,
        guidance_scale: options.guidance || 7.5,
        seed: options.seed,
      });

      setActiveJobs(prev => new Map(prev).set(job.job_id, job));
      
      // Poll for completion
      const result = await client.pollJobUntilComplete(job.job_id, (updatedJob) => {
        setActiveJobs(prev => new Map(prev).set(job.job_id, updatedJob));
      });

      if (result.status === 'completed') {
        setResults(prev => new Map(prev).set(job.job_id, result.result));
        setActiveJobs(prev => {
          const newMap = new Map(prev);
          newMap.delete(job.job_id);
          return newMap;
        });
      } else if (result.status === 'failed') {
        setErrors(prev => new Map(prev).set(job.job_id, {
          message: result.error || 'Generation failed',
          code: 'GENERATION_FAILED',
          details: result
        }));
      }

      return result;
    } catch (err) {
      if (err instanceof InferenceAPIError) {
        const errorId = Math.random().toString(36);
        setErrors(prev => new Map(prev).set(errorId, {
          message: err.message,
          code: err.code,
          details: err.details,
        }));
      }
      throw err;
    }
  }, [client]);

  const generateText = useCallback(async (
    prompt: string,
    options: {
      model?: string;
      maxTokens?: number;
      temperature?: number;
      topP?: number;
    } = {}
  ) => {
    try {
      const job = await client.generateText({
        model: options.model || 'llama2-7b-chat',
        prompt,
        max_tokens: options.maxTokens || 512,
        temperature: options.temperature || 0.7,
        top_p: options.topP || 0.9,
      });

      setActiveJobs(prev => new Map(prev).set(job.job_id, job));
      
      const result = await client.pollJobUntilComplete(job.job_id, (updatedJob) => {
        setActiveJobs(prev => new Map(prev).set(job.job_id, updatedJob));
      });

      if (result.status === 'completed') {
        setResults(prev => new Map(prev).set(job.job_id, result.result));
        setActiveJobs(prev => {
          const newMap = new Map(prev);
          newMap.delete(job.job_id);
          return newMap;
        });
      }

      return result;
    } catch (err) {
      if (err instanceof InferenceAPIError) {
        const errorId = Math.random().toString(36);
        setErrors(prev => new Map(prev).set(errorId, {
          message: err.message,
          code: err.code,
          details: err.details,
        }));
      }
      throw err;
    }
  }, [client]);

  const generateAudio = useCallback(async (
    prompt: string,
    options: {
      model?: string;
      duration?: number;
      temperature?: number;
    } = {}
  ) => {
    try {
      const job = await client.generateAudio({
        model: options.model || 'musicgen-medium',
        prompt,
        duration: options.duration || 30,
        temperature: options.temperature || 1.0,
      });

      setActiveJobs(prev => new Map(prev).set(job.job_id, job));
      
      const result = await client.pollJobUntilComplete(job.job_id, (updatedJob) => {
        setActiveJobs(prev => new Map(prev).set(job.job_id, updatedJob));
      });

      if (result.status === 'completed') {
        setResults(prev => new Map(prev).set(job.job_id, result.result));
        setActiveJobs(prev => {
          const newMap = new Map(prev);
          newMap.delete(job.job_id);
          return newMap;
        });
      }

      return result;
    } catch (err) {
      if (err instanceof InferenceAPIError) {
        const errorId = Math.random().toString(36);
        setErrors(prev => new Map(prev).set(errorId, {
          message: err.message,
          code: err.code,
          details: err.details,
        }));
      }
      throw err;
    }
  }, [client]);

  const cancelJob = useCallback(async (jobId: string) => {
    try {
      await client.cancelJob(jobId);
      setActiveJobs(prev => {
        const newMap = new Map(prev);
        newMap.delete(jobId);
        return newMap;
      });
    } catch (err) {
      // Handle cancellation errors
      console.error('Failed to cancel job:', err);
    }
  }, [client]);

  const clearError = useCallback((errorId: string) => {
    setErrors(prev => {
      const newMap = new Map(prev);
      newMap.delete(errorId);
      return newMap;
    });
  }, []);

  const clearResult = useCallback((jobId: string) => {
    setResults(prev => {
      const newMap = new Map(prev);
      newMap.delete(jobId);
      return newMap;
    });
  }, []);

  return {
    activeJobs: Array.from(activeJobs.values()),
    results: Array.from(results.entries()),
    errors: Array.from(errors.entries()),
    generateImage,
    generateText,
    generateAudio,
    cancelJob,
    clearError,
    clearResult,
    isGenerating: activeJobs.size > 0,
  };
}