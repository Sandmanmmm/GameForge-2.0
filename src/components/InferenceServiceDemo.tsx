/**
 * Inference Service Integration Demo Component
 * 
 * Demonstrates how to integrate the new secure inference service
 * with existing GameForge UI components.
 */

import React, { useState } from 'react';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

// Import the adapter for gradual migration
import { 
  generateAssets, 
  generateText, 
  pollJobUntilComplete,
  getInferenceServiceStatus,
  getAvailableModels,
  LegacyAssetGenerationRequest,
  LegacyTextGenerationRequest 
} from '../services/inferenceAdapter';

// Import the raw client for advanced features
import { inferenceClient } from '../services/inference';

interface GenerationJob {
  id: string;
  type: 'image' | 'text' | 'audio';
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  result?: any;
  error?: string;
  startTime: Date;
}

export function InferenceServiceDemo() {
  const [prompt, setPrompt] = useState('');
  const [generationType, setGenerationType] = useState<'image' | 'text' | 'audio'>('image');
  const [quality, setQuality] = useState<'draft' | 'standard' | 'high' | 'ultra'>('standard');
  const [provider, setProvider] = useState<'inference' | 'huggingface' | 'replicate'>('inference');
  const [activeJobs, setActiveJobs] = useState<GenerationJob[]>([]);
  const [serviceStatus, setServiceStatus] = useState<any>(null);
  const [availableModels, setAvailableModels] = useState<any[]>([]);

  // Check service status on component mount
  React.useEffect(() => {
    checkServiceStatus();
    loadAvailableModels();
  }, []);

  const checkServiceStatus = async () => {
    try {
      const status = await getInferenceServiceStatus();
      setServiceStatus(status);
    } catch (error) {
      console.error('Failed to check service status:', error);
    }
  };

  const loadAvailableModels = async () => {
    try {
      const models = await getAvailableModels();
      setAvailableModels(models);
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) return;

    const jobId = Date.now().toString();
    const newJob: GenerationJob = {
      id: jobId,
      type: generationType,
      status: 'pending',
      progress: 0,
      startTime: new Date(),
    };

    setActiveJobs(prev => [...prev, newJob]);

    try {
      if (generationType === 'image') {
        await generateImageWithAdapter(jobId);
      } else if (generationType === 'text') {
        await generateTextWithAdapter(jobId);
      } else if (generationType === 'audio') {
        await generateAudioDirect(jobId);
      }
    } catch (error) {
      updateJob(jobId, { status: 'failed', error: error instanceof Error ? error.message : 'Unknown error' });
    }
  };

  const generateImageWithAdapter = async (jobId: string) => {
    const request: LegacyAssetGenerationRequest = {
      prompt,
      assetType: 'concept art',
      style: 'digital art',
      size: '1024x1024',
      count: 1,
      quality,
      provider,
    };

    try {
      const response = await generateAssets(request);
      
      if (response.jobId) {
        // Job-based response - poll for completion
        updateJob(jobId, { status: 'running' });
        
        const result = await pollJobUntilComplete(response.jobId, (progress) => {
          updateJob(jobId, { 
            progress: progress.progress || 0,
            status: progress.status === 'completed' ? 'completed' : 'running'
          });
        });
        
        updateJob(jobId, { 
          status: 'completed', 
          result: result.result,
          progress: 100 
        });
      } else if (response.assets) {
        // Direct response
        updateJob(jobId, { 
          status: 'completed', 
          result: response.assets,
          progress: 100 
        });
      }
    } catch (error) {
      updateJob(jobId, { 
        status: 'failed', 
        error: error instanceof Error ? error.message : 'Generation failed' 
      });
    }
  };

  const generateTextWithAdapter = async (jobId: string) => {
    const request: LegacyTextGenerationRequest = {
      prompt,
      gameType: 'RPG',
      complexity: 'medium',
      provider,
      maxTokens: 512,
      temperature: 0.7,
    };

    try {
      updateJob(jobId, { status: 'running' });
      const response = await generateText(request);
      
      updateJob(jobId, { 
        status: 'completed', 
        result: { text: response.text },
        progress: 100 
      });
    } catch (error) {
      updateJob(jobId, { 
        status: 'failed', 
        error: error instanceof Error ? error.message : 'Generation failed' 
      });
    }
  };

  const generateAudioDirect = async (jobId: string) => {
    try {
      updateJob(jobId, { status: 'running' });
      
      const job = await inferenceClient.generateAudio({
        model: 'musicgen-medium',
        prompt,
        duration: 30,
        temperature: 1.0,
      });

      const result = await inferenceClient.pollJobUntilComplete(job.job_id, (updatedJob) => {
        updateJob(jobId, { 
          progress: (updatedJob.progress || 0) * 100,
          status: updatedJob.status === 'completed' ? 'completed' : 'running'
        });
      });

      updateJob(jobId, { 
        status: 'completed', 
        result: result.result,
        progress: 100 
      });
    } catch (error) {
      updateJob(jobId, { 
        status: 'failed', 
        error: error instanceof Error ? error.message : 'Generation failed' 
      });
    }
  };

  const updateJob = (jobId: string, updates: Partial<GenerationJob>) => {
    setActiveJobs(prev => prev.map(job => 
      job.id === jobId ? { ...job, ...updates } : job
    ));
  };

  const clearJob = (jobId: string) => {
    setActiveJobs(prev => prev.filter(job => job.id !== jobId));
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Inference Service Demo</h2>
        
        {serviceStatus && (
          <div className="flex items-center space-x-2">
            <Badge variant={serviceStatus.available ? 'default' : 'destructive'}>
              {serviceStatus.available ? 'Connected' : 'Offline'}
            </Badge>
            {serviceStatus.stats && (
              <Badge variant="outline">
                {serviceStatus.stats.models_loaded} models loaded
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* Generation Controls */}
      <Card className="p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-sm font-medium">Generation Type</label>
            <Select value={generationType} onValueChange={(value: any) => setGenerationType(value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="image">Image Generation</SelectItem>
                <SelectItem value="text">Text Generation</SelectItem>
                <SelectItem value="audio">Audio Generation</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium">Quality</label>
            <Select value={quality} onValueChange={(value: any) => setQuality(value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="draft">Draft (Fast)</SelectItem>
                <SelectItem value="standard">Standard</SelectItem>
                <SelectItem value="high">High Quality</SelectItem>
                <SelectItem value="ultra">Ultra (Slow)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium">Provider</label>
            <Select value={provider} onValueChange={(value: any) => setProvider(value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="inference">Secure Inference Service</SelectItem>
                <SelectItem value="huggingface">Hugging Face</SelectItem>
                <SelectItem value="replicate">Replicate</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div>
          <label className="text-sm font-medium">Prompt</label>
          <Textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter your generation prompt..."
            rows={3}
          />
        </div>

        <Button 
          onClick={handleGenerate} 
          disabled={!prompt.trim() || !serviceStatus?.available}
          className="w-full"
        >
          Generate {generationType.charAt(0).toUpperCase() + generationType.slice(1)}
        </Button>
      </Card>

      {/* Active Jobs */}
      {activeJobs.length > 0 && (
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4">Active Generations</h3>
          <div className="space-y-3">
            {activeJobs.map((job) => (
              <div key={job.id} className="border rounded p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Badge variant="outline">{job.type}</Badge>
                    <Badge variant={
                      job.status === 'completed' ? 'default' :
                      job.status === 'failed' ? 'destructive' :
                      'secondary'
                    }>
                      {job.status}
                    </Badge>
                  </div>
                  
                  {job.status === 'completed' || job.status === 'failed' ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => clearJob(job.id)}
                    >
                      Clear
                    </Button>
                  ) : null}
                </div>

                {job.status === 'running' && (
                  <Progress value={job.progress} className="w-full" />
                )}

                {job.error && (
                  <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                    {job.error}
                  </div>
                )}

                {job.result && job.status === 'completed' && (
                  <div className="text-sm bg-green-50 p-2 rounded">
                    <strong>Result:</strong> Generation completed successfully!
                    {job.type === 'text' && job.result.text && (
                      <div className="mt-2 p-2 bg-white rounded border">
                        {job.result.text.substring(0, 200)}...
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Available Models */}
      {availableModels.length > 0 && (
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4">Available Models</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {availableModels.map((model) => (
              <div key={model.name} className="border rounded p-3">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium">{model.name}</h4>
                  <Badge variant={
                    model.status === 'available' ? 'default' :
                    model.status === 'loading' ? 'secondary' :
                    'destructive'
                  }>
                    {model.status}
                  </Badge>
                </div>
                <p className="text-sm text-gray-600">{model.description}</p>
                {model.license && (
                  <Badge variant="outline" className="mt-2 text-xs">
                    {model.license}
                  </Badge>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}