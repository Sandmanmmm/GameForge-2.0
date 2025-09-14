import React, { useState, useEffect } from 'react'
import { JobMetadata, pollJobUntilComplete } from '../lib/aiAPI'

interface JobTrackerProps {
  jobId: string
  onComplete?: (job: JobMetadata) => void
  onError?: (error: string) => void
  autoStart?: boolean
}

export const JobTracker: React.FC<JobTrackerProps> = ({
  jobId,
  onComplete,
  onError,
  autoStart = true
}) => {
  const [job, setJob] = useState<JobMetadata | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startPolling = async () => {
    if (isPolling) return;
    
    setIsPolling(true);
    setError(null);
    
    try {
      const completedJob = await pollJobUntilComplete(
        jobId,
        (jobUpdate) => {
          setJob(jobUpdate);
        },
        2000, // Poll every 2 seconds
        300000 // 5 minute timeout
      );
      
      setJob(completedJob);
      setIsPolling(false);
      onComplete?.(completedJob);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      setIsPolling(false);
      onError?.(errorMessage);
    }
  };

  useEffect(() => {
    if (autoStart && jobId) {
      startPolling();
    }
  }, [jobId, autoStart]);

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center space-x-2">
          <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          <span className="text-red-700 font-medium">Job Failed</span>
        </div>
        <p className="text-red-600 mt-1">{error}</p>
        <button
          onClick={() => {
            setError(null);
            startPolling();
          }}
          className="mt-2 px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
          <span className="text-blue-700 font-medium">Starting job...</span>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-700 bg-green-50 border-green-200';
      case 'failed': return 'text-red-700 bg-red-50 border-red-200';
      case 'processing': return 'text-blue-700 bg-blue-50 border-blue-200';
      case 'pending': return 'text-yellow-700 bg-yellow-50 border-yellow-200';
      case 'cancelled': return 'text-gray-700 bg-gray-50 border-gray-200';
      default: return 'text-gray-700 bg-gray-50 border-gray-200';
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <div className={`border rounded-lg p-4 ${getStatusColor(job.status)}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          {job.status === 'processing' && (
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-current"></div>
          )}
          {job.status === 'completed' && (
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          )}
          <span className="font-medium capitalize">{job.status}</span>
        </div>
        <span className="text-sm font-mono">{job.id}</span>
      </div>

      {/* Progress Bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-sm mb-1">
          <span>Progress</span>
          <span>{Math.round(job.progress)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-current h-2 rounded-full transition-all duration-300"
            style={{ width: `${job.progress}%` }}
          ></div>
        </div>
      </div>

      {/* Current Stage */}
      {job.metadata?.current_stage && (
        <div className="mb-3">
          <span className="text-sm font-medium">Current Stage: </span>
          <span className="text-sm">{job.metadata.current_stage}</span>
        </div>
      )}

      {/* Timing Information */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="font-medium">Started:</span>
          <br />
          <span className="text-xs">{formatTime(job.created_at)}</span>
        </div>
        <div>
          <span className="font-medium">Updated:</span>
          <br />
          <span className="text-xs">{formatTime(job.updated_at)}</span>
        </div>
      </div>

      {/* Estimated Completion */}
      {job.estimated_completion && job.status === 'processing' && (
        <div className="mt-3 text-sm">
          <span className="font-medium">Est. Completion: </span>
          <span className="text-xs">{formatTime(job.estimated_completion)}</span>
        </div>
      )}

      {/* Error Message */}
      {job.error_message && (
        <div className="mt-3 p-2 bg-red-100 border border-red-300 rounded text-sm">
          <span className="font-medium text-red-700">Error: </span>
          <span className="text-red-600">{job.error_message}</span>
        </div>
      )}
    </div>
  );
};