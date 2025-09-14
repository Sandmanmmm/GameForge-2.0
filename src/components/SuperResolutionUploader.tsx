import React, { useState, useCallback } from 'react'
import { superResolution, SuperResRequest, JobMetadata } from '../lib/aiAPI'
import { JobTracker } from './JobTracker'
import { JobResultDisplay } from './JobResultDisplay'

interface SuperResolutionUploaderProps {
  onComplete?: (job: JobMetadata) => void
  onError?: (error: string) => void
  className?: string
}

export const SuperResolutionUploader: React.FC<SuperResolutionUploaderProps> = ({
  onComplete,
  onError,
  className = ''
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [completedJob, setCompletedJob] = useState<JobMetadata | null>(null)
  const [dragActive, setDragActive] = useState(false)

  // Super-resolution settings
  const [scaleFactor, setScaleFactor] = useState(2)
  const [enhanceDetails, setEnhanceDetails] = useState(true)
  const [preserveStyle, setPreserveStyle] = useState(true)
  const [noiseReduction, setNoiseReduction] = useState(0.5)
  const [model, setModel] = useState('real-esrgan')

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return

    const file = files[0]
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
      onError?.('Please select an image file')
      return
    }

    // Validate file size (50MB limit)
    const maxSize = 50 * 1024 * 1024
    if (file.size > maxSize) {
      onError?.('File too large. Maximum size: 50MB')
      return
    }

    setSelectedFile(file)
  }, [onError])

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
  }, [])

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files)
  }, [handleFiles])

  const handleUpscale = async () => {
    if (!selectedFile) return

    setIsUploading(true)
    setCompletedJob(null)

    try {
      const request: SuperResRequest = {
        scale_factor: scaleFactor,
        enhance_details: enhanceDetails,
        preserve_style: preserveStyle,
        noise_reduction: noiseReduction,
        model: model
      }

      const response = await superResolution(request, selectedFile)

      if (response.success && response.data) {
        setCurrentJobId(response.data.job_id)
      } else {
        throw new Error(response.error?.message || 'Upload failed')
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      onError?.(errorMessage)
      setIsUploading(false)
    }
  }

  const handleJobComplete = (job: JobMetadata) => {
    setCompletedJob(job)
    setCurrentJobId(null)
    setIsUploading(false)
    onComplete?.(job)
  }

  const handleJobError = (error: string) => {
    setCurrentJobId(null)
    setIsUploading(false)
    onError?.(error)
  }

  const resetUploader = () => {
    setSelectedFile(null)
    setCurrentJobId(null)
    setCompletedJob(null)
    setIsUploading(false)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className={`bg-white border border-gray-200 rounded-lg overflow-hidden ${className}`}>
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-pink-600 p-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-white/20 rounded-lg">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">AI Super-Resolution</h3>
            <p className="text-sm text-purple-100">Enhance image quality with AI upscaling</p>
          </div>
        </div>
      </div>

      <div className="p-6">
        {/* File Upload Area */}
        {!selectedFile && !currentJobId && !completedJob && (
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive 
                ? 'border-purple-500 bg-purple-50' 
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" stroke="currentColor" fill="none" viewBox="0 0 48 48">
              <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <p className="text-lg font-medium text-gray-900 mb-2">Drop image here or click to upload</p>
            <p className="text-sm text-gray-500 mb-4">PNG, JPG, WEBP up to 50MB</p>
            <input
              type="file"
              accept="image/*"
              onChange={handleFileInput}
              className="hidden"
              id="image-upload"
            />
            <label
              htmlFor="image-upload"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700 cursor-pointer transition-colors"
            >
              Choose File
            </label>
          </div>
        )}

        {/* File Info & Settings */}
        {selectedFile && !currentJobId && !completedJob && (
          <div className="space-y-6">
            {/* File Info */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center space-x-4">
                <div className="flex-shrink-0">
                  <img
                    src={URL.createObjectURL(selectedFile)}
                    alt="Preview"
                    className="w-16 h-16 object-cover rounded-lg"
                  />
                </div>
                <div className="flex-grow min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{selectedFile.name}</p>
                  <p className="text-sm text-gray-500">{formatFileSize(selectedFile.size)}</p>
                </div>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Super-Resolution Settings */}
            <div className="space-y-4">
              <h4 className="text-lg font-medium text-gray-900">Enhancement Settings</h4>
              
              {/* Scale Factor */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Scale Factor: {scaleFactor}x
                </label>
                <div className="flex space-x-2">
                  {[2, 4, 8].map((factor) => (
                    <button
                      key={factor}
                      onClick={() => setScaleFactor(factor)}
                      className={`px-3 py-2 text-sm rounded-md ${
                        scaleFactor === factor
                          ? 'bg-purple-600 text-white'
                          : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      }`}
                    >
                      {factor}x
                    </button>
                  ))}
                </div>
              </div>

              {/* Model Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">AI Model</label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="real-esrgan">Real-ESRGAN (Best for photos)</option>
                  <option value="esrgan">ESRGAN (General purpose)</option>
                  <option value="waifu2x">Waifu2x (Best for anime/art)</option>
                </select>
              </div>

              {/* Enhancement Options */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-gray-700">Enhance Details</label>
                  <input
                    type="checkbox"
                    checked={enhanceDetails}
                    onChange={(e) => setEnhanceDetails(e.target.checked)}
                    className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                  />
                </div>
                
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-gray-700">Preserve Style</label>
                  <input
                    type="checkbox"
                    checked={preserveStyle}
                    onChange={(e) => setPreserveStyle(e.target.checked)}
                    className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Noise Reduction: {Math.round(noiseReduction * 100)}%
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={noiseReduction}
                    onChange={(e) => setNoiseReduction(parseFloat(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  />
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex space-x-3">
              <button
                onClick={handleUpscale}
                disabled={isUploading}
                className="flex-1 bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 disabled:opacity-50 transition-colors"
              >
                {isUploading ? 'Starting Enhancement...' : 'Enhance Image'}
              </button>
              <button
                onClick={() => setSelectedFile(null)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Job Tracking */}
        {currentJobId && (
          <div className="space-y-4">
            <h4 className="text-lg font-medium text-gray-900">Enhancement Progress</h4>
            <JobTracker
              jobId={currentJobId}
              onComplete={handleJobComplete}
              onError={handleJobError}
            />
          </div>
        )}

        {/* Completed Job Display */}
        {completedJob && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-lg font-medium text-gray-900">Enhancement Complete</h4>
              <button
                onClick={resetUploader}
                className="text-sm text-purple-600 hover:text-purple-700"
              >
                Enhance Another Image
              </button>
            </div>
            <JobResultDisplay
              job={completedJob}
              onDownload={(url) => {
                const link = document.createElement('a')
                link.href = url
                link.download = `enhanced_${selectedFile?.name || 'image'}`
                link.click()
              }}
              onVariationRequest={(job) => {
                // Reset for new enhancement with similar settings
                setCompletedJob(null)
                setSelectedFile(null)
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}