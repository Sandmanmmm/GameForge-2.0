import React, { useState } from 'react'
import { AIAssetGenerator } from './AIAssetGenerator'
import { SuperResolutionUploader } from './SuperResolutionUploader'
import { JobMetadata } from '../lib/aiAPI'

interface AIDemoPageProps {
  className?: string
}

export const AIDemoPage: React.FC<AIDemoPageProps> = ({ className = '' }) => {
  const [activeTab, setActiveTab] = useState<'generate' | 'superres'>('generate')
  const [generatedAssets, setGeneratedAssets] = useState<any[]>([])
  const [enhancedAssets, setEnhancedAssets] = useState<JobMetadata[]>([])
  const [notifications, setNotifications] = useState<Array<{
    id: string
    message: string
    type: 'success' | 'error'
    timestamp: Date
  }>>([])

  const addNotification = (message: string, type: 'success' | 'error') => {
    const notification = {
      id: Date.now().toString(),
      message,
      type,
      timestamp: new Date()
    }
    setNotifications(prev => [notification, ...prev.slice(0, 4)]) // Keep only 5 most recent

    // Auto-remove after 5 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== notification.id))
    }, 5000)
  }

  const handleAssetGenerated = (asset: any) => {
    setGeneratedAssets(prev => [asset, ...prev])
    addNotification(`Generated asset: ${asset.name}`, 'success')
  }

  const handleSuperResComplete = (job: JobMetadata) => {
    setEnhancedAssets(prev => [job, ...prev])
    addNotification(`Enhanced image completed`, 'success')
  }

  const handleError = (error: string) => {
    addNotification(error, 'error')
  }

  return (
    <div className={`min-h-screen bg-gray-50 ${className}`}>
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <div className="p-2 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">AI Asset Studio</h1>
                <p className="text-sm text-gray-500">Generate and enhance game assets with AI</p>
              </div>
            </div>

            {/* Tab Navigation */}
            <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setActiveTab('generate')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  activeTab === 'generate'
                    ? 'bg-white text-purple-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Generate Assets
              </button>
              <button
                onClick={() => setActiveTab('superres')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  activeTab === 'superres'
                    ? 'bg-white text-purple-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Super-Resolution
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Notifications */}
      {notifications.length > 0 && (
        <div className="fixed top-4 right-4 z-50 space-y-2">
          {notifications.map((notification) => (
            <div
              key={notification.id}
              className={`max-w-sm w-full bg-white shadow-lg rounded-lg pointer-events-auto overflow-hidden border-l-4 ${
                notification.type === 'success' ? 'border-green-500' : 'border-red-500'
              }`}
            >
              <div className="p-4">
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    {notification.type === 'success' ? (
                      <svg className="h-6 w-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    ) : (
                      <svg className="h-6 w-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    )}
                  </div>
                  <div className="ml-3 w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900">{notification.message}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {notification.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                  <div className="ml-4 flex-shrink-0 flex">
                    <button
                      onClick={() => setNotifications(prev => prev.filter(n => n.id !== notification.id))}
                      className="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500"
                    >
                      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* AI Tool Panel */}
          <div className="lg:col-span-2">
            {activeTab === 'generate' && (
              <AIAssetGenerator
                onAssetGenerated={handleAssetGenerated}
                className="h-full"
              />
            )}
            {activeTab === 'superres' && (
              <SuperResolutionUploader
                onComplete={handleSuperResComplete}
                onError={handleError}
                className="h-full"
              />
            )}
          </div>

          {/* Results Panel */}
          <div className="space-y-6">
            {/* Generated Assets */}
            {activeTab === 'generate' && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Generated Assets ({generatedAssets.length})
                </h3>
                {generatedAssets.length === 0 ? (
                  <div className="text-center py-8">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 48 48">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M34 40h10v-4a6 6 0 00-10.712-3.714M34 40H14m20 0v-4a9.971 9.971 0 00-.712-3.714M14 40H4v-4a6 6 0 0110.712-3.714M14 40v-4a9.971 9.971 0 01.712-3.714M18 24a6 6 0 11-12 0 6 6 0 0112 0zm0 0a6 6 0 11-12 0 6 6 0 0112 0z" />
                    </svg>
                    <p className="mt-2 text-sm text-gray-500">No assets generated yet</p>
                    <p className="text-xs text-gray-400">Use the generator to create your first asset</p>
                  </div>
                ) : (
                  <div className="space-y-4 max-h-96 overflow-y-auto">
                    {generatedAssets.map((asset, index) => (
                      <div key={asset.id || index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                        <img
                          src={asset.src || asset.thumbnail}
                          alt={asset.name}
                          className="w-12 h-12 object-cover rounded-lg"
                        />
                        <div className="flex-grow min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">{asset.name}</p>
                          <p className="text-xs text-gray-500">{asset.style} • {asset.resolution}</p>
                        </div>
                        <button
                          onClick={() => window.open(asset.src, '_blank')}
                          className="text-purple-600 hover:text-purple-700"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Enhanced Assets */}
            {activeTab === 'superres' && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Enhanced Images ({enhancedAssets.length})
                </h3>
                {enhancedAssets.length === 0 ? (
                  <div className="text-center py-8">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 48 48">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p className="mt-2 text-sm text-gray-500">No enhanced images yet</p>
                    <p className="text-xs text-gray-400">Upload an image to enhance with AI</p>
                  </div>
                ) : (
                  <div className="space-y-4 max-h-96 overflow-y-auto">
                    {enhancedAssets.map((job, index) => (
                      <div key={job.id || index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                        <img
                          src={job.asset_url}
                          alt="Enhanced"
                          className="w-12 h-12 object-cover rounded-lg"
                        />
                        <div className="flex-grow min-w-0">
                          <p className="text-sm font-medium text-gray-900">Enhanced Image</p>
                          <p className="text-xs text-gray-500">
                            {job.metadata?.scale_factor}x upscale • {job.metadata?.model}
                          </p>
                        </div>
                        <button
                          onClick={() => window.open(job.asset_url!, '_blank')}
                          className="text-purple-600 hover:text-purple-700"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* API Status */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">API Status</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Generation API</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Ready
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Super-Resolution API</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Ready
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Job Tracking</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Active
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}