import React from 'react'
import { JobMetadata } from '../lib/aiAPI'

interface JobResultDisplayProps {
  job: JobMetadata
  onDownload?: (url: string) => void
  onVariationRequest?: (job: JobMetadata) => void
  className?: string
}

export const JobResultDisplay: React.FC<JobResultDisplayProps> = ({
  job,
  onDownload,
  onVariationRequest,
  className = ''
}) => {
  if (job.status !== 'completed' || !job.asset_url) {
    return null
  }

  const handleDownload = () => {
    if (job.asset_url && onDownload) {
      onDownload(job.asset_url)
    }
  }

  const handleVariationRequest = () => {
    if (onVariationRequest) {
      onVariationRequest(job)
    }
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  const isImageAsset = job.asset_url.match(/\.(jpg|jpeg|png|gif|webp)$/i)
  const isAudioAsset = job.asset_url.match(/\.(mp3|wav|ogg)$/i)

  return (
    <div className={`bg-white border border-gray-200 rounded-lg overflow-hidden ${className}`}>
      {/* Asset Preview */}
      <div className="relative">
        {isImageAsset && (
          <img 
            src={job.asset_url} 
            alt={job.metadata?.prompt || 'Generated asset'}
            className="w-full h-64 object-cover"
            onError={(e) => {
              // Fallback for broken images
              e.currentTarget.src = '/api/placeholder/400/300?text=Generated+Asset'
            }}
          />
        )}
        
        {isAudioAsset && (
          <div className="w-full h-64 bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
            <div className="text-center text-white">
              <svg className="w-16 h-16 mx-auto mb-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.707.707L4.586 13H2a1 1 0 01-1-1V8a1 1 0 011-1h2.586l3.707-3.707a1 1 0 011.09-.217zM15.657 6.343a1 1 0 011.414 0A9.972 9.972 0 0119 12a9.972 9.972 0 01-1.929 5.657 1 1 0 01-1.414-1.414A7.971 7.971 0 0017 12a7.971 7.971 0 00-1.343-4.243 1 1 0 010-1.414z" clipRule="evenodd" />
                <path fillRule="evenodd" d="M13.828 7.172a1 1 0 011.414 0A5.983 5.983 0 0117 12a5.983 5.983 0 01-1.758 4.828 1 1 0 01-1.414-1.414A3.987 3.987 0 0015 12a3.987 3.987 0 00-1.172-2.828 1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
              <p className="text-lg font-medium">Audio Asset</p>
            </div>
          </div>
        )}

        {!isImageAsset && !isAudioAsset && (
          <div className="w-full h-64 bg-gradient-to-br from-blue-500 to-green-500 flex items-center justify-center">
            <div className="text-center text-white">
              <svg className="w-16 h-16 mx-auto mb-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 0v12h8V4H6z" clipRule="evenodd" />
              </svg>
              <p className="text-lg font-medium">Generated Asset</p>
            </div>
          </div>
        )}

        {/* Status Badge */}
        <div className="absolute top-2 right-2">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            Completed
          </span>
        </div>
      </div>

      {/* Asset Information */}
      <div className="p-4">
        {/* Prompt */}
        {job.metadata?.prompt && (
          <div className="mb-3">
            <h3 className="text-sm font-medium text-gray-900 mb-1">Prompt</h3>
            <p className="text-sm text-gray-600 italic">"{job.metadata.prompt}"</p>
          </div>
        )}

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
          {job.metadata?.style && (
            <div>
              <span className="font-medium text-gray-700">Style:</span>
              <br />
              <span className="text-gray-600 capitalize">{job.metadata.style}</span>
            </div>
          )}
          
          {job.metadata?.dimensions && (
            <div>
              <span className="font-medium text-gray-700">Dimensions:</span>
              <br />
              <span className="text-gray-600">{job.metadata.dimensions}</span>
            </div>
          )}
          
          {job.metadata?.quality && (
            <div>
              <span className="font-medium text-gray-700">Quality:</span>
              <br />
              <span className="text-gray-600 capitalize">{job.metadata.quality}</span>
            </div>
          )}
          
          {job.metadata?.model && (
            <div>
              <span className="font-medium text-gray-700">Model:</span>
              <br />
              <span className="text-gray-600">{job.metadata.model}</span>
            </div>
          )}
        </div>

        {/* Generation Time */}
        <div className="mb-4 text-sm">
          <span className="font-medium text-gray-700">Generated:</span>
          <br />
          <span className="text-gray-600">{formatTime(job.created_at)}</span>
        </div>

        {/* Audio Controls */}
        {isAudioAsset && (
          <div className="mb-4">
            <audio controls className="w-full">
              <source src={job.asset_url} type="audio/mpeg" />
              Your browser does not support the audio element.
            </audio>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleDownload}
            className="flex items-center px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium transition-colors"
          >
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download
          </button>

          {onVariationRequest && job.metadata?.prompt && (
            <button
              onClick={handleVariationRequest}
              className="flex items-center px-3 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm font-medium transition-colors"
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Create Variation
            </button>
          )}

          <button
            onClick={() => window.open(job.asset_url, '_blank')}
            className="flex items-center px-3 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm font-medium transition-colors"
          >
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            Open
          </button>
        </div>

        {/* Job ID (for debugging/support) */}
        <div className="mt-3 pt-3 border-t border-gray-200">
          <p className="text-xs text-gray-400 font-mono">Job ID: {job.id}</p>
        </div>
      </div>
    </div>
  )
}