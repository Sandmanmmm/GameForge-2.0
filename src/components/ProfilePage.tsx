import React, { useContext, useState } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { AuthContext } from '@/contexts/AuthContext'
// Import icons directly to bypass proxy issues
import { User } from '@phosphor-icons/react/dist/csr/User'
import { Gear } from '@phosphor-icons/react/dist/csr/Gear'
import { Envelope } from '@phosphor-icons/react/dist/csr/Envelope'
import { Calendar } from '@phosphor-icons/react/dist/csr/Calendar'
import { Shield } from '@phosphor-icons/react/dist/csr/Shield'
import { CaretRight } from '@phosphor-icons/react/dist/csr/CaretRight'
import { ArrowLeft } from '@phosphor-icons/react/dist/csr/ArrowLeft'
import { Pencil } from '@phosphor-icons/react/dist/csr/Pencil'
import { Check } from '@phosphor-icons/react/dist/csr/Check'
import { X } from '@phosphor-icons/react/dist/csr/X'

interface ProfilePageProps {
  onBack: () => void
  onSettingsOpen: () => void
}

export function ProfilePage({ onBack, onSettingsOpen }: ProfilePageProps) {
  const { user, updateUserProfile } = useContext(AuthContext)
  const [activeTab, setActiveTab] = useState('overview')
  const [isEditingDisplayName, setIsEditingDisplayName] = useState(false)
  const [displayName, setDisplayName] = useState(user?.name || '')
  const [isUpdating, setIsUpdating] = useState(false)

  // Debug logging to see what user data we have
  console.log('ProfilePage user object:', user)
  console.log('Current displayName state:', displayName)

  // Update displayName when user changes (important for OAuth flow)
  React.useEffect(() => {
    console.log('useEffect triggered - user.name changed to:', user?.name)
    if (user?.name !== undefined) {
      setDisplayName(user.name || '')
    }
  }, [user?.name])

  const handleSaveDisplayName = async () => {
    if (!displayName.trim()) {
      return
    }
    
    console.log('Saving display name:', displayName.trim())
    setIsUpdating(true)
    try {
      await updateUserProfile({ name: displayName.trim() })
      console.log('✅ Display name updated successfully')
      console.log('Updated user object:', user)
      setIsEditingDisplayName(false)
    } catch (error) {
      console.error('❌ Failed to update display name:', error)
      // Reset to original value on error
      setDisplayName(user?.name || '')
    } finally {
      setIsUpdating(false)
    }
  }

  const handleCancelEdit = () => {
    setDisplayName(user?.name || '')
    setIsEditingDisplayName(false)
  }

  if (!user) {
    return (
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex-1 p-6 flex items-center justify-center"
      >
        <Card className="w-full max-w-md">
          <CardContent className="p-6 text-center">
            <User size={48} className="mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold mb-2">Not Signed In</h3>
            <p className="text-muted-foreground">Please sign in to view your profile.</p>
          </CardContent>
        </Card>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex-1 p-6 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={onBack}
            className="gap-2"
          >
            <ArrowLeft size={16} />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Profile</h1>
            <p className="text-muted-foreground">Manage your account information and settings</p>
          </div>
        </div>
        <Button onClick={onSettingsOpen} className="gap-2">
          <Gear size={16} />
          Settings
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Overview */}
        <div className="lg:col-span-2 space-y-6">
          {/* User Info Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User size={20} />
                Account Information
              </CardTitle>
              <CardDescription>
                Your basic account details and profile information
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-accent/20 flex items-center justify-center">
                  <User size={24} className="text-accent" />
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold">{user.name || 'User'}</h3>
                  <p className="text-muted-foreground flex items-center gap-2">
                    <Envelope size={16} />
                    {user.email}
                  </p>
                </div>
              </div>

              <Separator />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-muted-foreground">Display Name</label>
                    {!isEditingDisplayName && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setIsEditingDisplayName(true)}
                        className="h-6 px-2 text-xs"
                      >
                        <Pencil size={12} className="mr-1" />
                        Edit
                      </Button>
                    )}
                  </div>
                  {isEditingDisplayName ? (
                    <div className="flex items-center gap-2">
                      <Input
                        value={displayName}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDisplayName(e.target.value)}
                        placeholder="Enter display name"
                        className="flex-1"
                        disabled={isUpdating}
                      />
                      <Button
                        size="sm"
                        onClick={handleSaveDisplayName}
                        disabled={isUpdating || !displayName.trim()}
                        className="h-8 px-2"
                      >
                        <Check size={12} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleCancelEdit}
                        disabled={isUpdating}
                        className="h-8 px-2"
                      >
                        <X size={12} />
                      </Button>
                    </div>
                  ) : (
                    <p className="text-sm">{user.name || 'Not set'}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-muted-foreground">Email Address</label>
                  <p className="text-sm">{user.email}</p>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-muted-foreground">User ID</label>
                  <p className="text-sm font-mono text-xs">{user.id}</p>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-muted-foreground">Account Status</label>
                  <Badge variant="secondary" className="w-fit">
                    <Shield size={12} className="mr-1" />
                    Active
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Account Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar size={20} />
                Account Activity
              </CardTitle>
              <CardDescription>
                Recent activity and account statistics
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <div>
                    <p className="font-medium">Last Sign In</p>
                    <p className="text-sm text-muted-foreground">Today at {new Date().toLocaleTimeString()}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <div>
                    <p className="font-medium">Account Created</p>
                    <p className="text-sm text-muted-foreground">Account information available</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions Sidebar */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
              <CardDescription>
                Manage your account and preferences
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button 
                variant="outline" 
                className="w-full justify-between"
                onClick={onSettingsOpen}
              >
                <span className="flex items-center gap-2">
                  <Gear size={16} />
                  Account Settings
                </span>
                <CaretRight size={16} />
              </Button>
              
              <Button 
                variant="outline" 
                className="w-full justify-between"
                onClick={onSettingsOpen}
              >
                <span className="flex items-center gap-2">
                  <Shield size={16} />
                  Privacy & Security
                </span>
                <CaretRight size={16} />
              </Button>
              
              <Button 
                variant="outline" 
                className="w-full justify-between"
                onClick={onSettingsOpen}
              >
                <span className="flex items-center gap-2">
                  <User size={16} />
                  Profile Settings
                </span>
                <CaretRight size={16} />
              </Button>
            </CardContent>
          </Card>

          {/* Account Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Account Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-accent mb-1">1</div>
                <div className="text-sm text-muted-foreground">Active Session</div>
              </div>
              <Separator />
              <div className="text-center">
                <div className="text-2xl font-bold text-accent mb-1">0</div>
                <div className="text-sm text-muted-foreground">Projects Created</div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </motion.div>
  )
}