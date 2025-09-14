import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { AuthContext } from '@/contexts/AuthContext'
import { useContext, useState } from 'react'
// Import icons directly to bypass proxy issues
import { ArrowLeft } from '@phosphor-icons/react/dist/csr/ArrowLeft'
import { User } from '@phosphor-icons/react/dist/csr/User'
import { Shield } from '@phosphor-icons/react/dist/csr/Shield'
import { Bell } from '@phosphor-icons/react/dist/csr/Bell'
import { Palette } from '@phosphor-icons/react/dist/csr/Palette'
import { Monitor } from '@phosphor-icons/react/dist/csr/Monitor'
import { Globe } from '@phosphor-icons/react/dist/csr/Globe'
import { FloppyDisk } from '@phosphor-icons/react/dist/csr/FloppyDisk'
import { Eye } from '@phosphor-icons/react/dist/csr/Eye'
import { EyeSlash } from '@phosphor-icons/react/dist/csr/EyeSlash'

interface SettingsPageProps {
  onBack: () => void
}

export function SettingsPage({ onBack }: SettingsPageProps) {
  const { user } = useContext(AuthContext)
  const [activeTab, setActiveTab] = useState('profile')
  const [hasChanges, setHasChanges] = useState(false)
  
  // Settings state
  const [profileSettings, setProfileSettings] = useState({
    displayName: user?.name || '',
    bio: '',
    publicProfile: false
  })
  
  const [notificationSettings, setNotificationSettings] = useState({
    emailNotifications: true,
    pushNotifications: false,
    projectUpdates: true,
    securityAlerts: true
  })
  
  const [appearanceSettings, setAppearanceSettings] = useState({
    theme: 'system',
    language: 'en',
    compactMode: false
  })
  
  const [securitySettings, setSecuritySettings] = useState({
    twoFactorEnabled: false,
    sessionTimeout: '24h',
    showLastSignIn: true
  })

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'appearance', label: 'Appearance', icon: Palette }
  ]

  const handleSave = () => {
    // TODO: Implement actual save functionality
    setHasChanges(false)
    console.log('Saving settings...', {
      profile: profileSettings,
      notifications: notificationSettings,
      appearance: appearanceSettings,
      security: securitySettings
    })
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Profile Information</CardTitle>
                <CardDescription>
                  Update your personal information and public profile settings
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="displayName">Display Name</Label>
                  <Input
                    id="displayName"
                    value={profileSettings.displayName}
                    onChange={(e) => {
                      setProfileSettings(prev => ({ ...prev, displayName: e.target.value }))
                      setHasChanges(true)
                    }}
                    placeholder="Enter your display name"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="bio">Bio</Label>
                  <Textarea
                    id="bio"
                    value={profileSettings.bio}
                    onChange={(e) => {
                      setProfileSettings(prev => ({ ...prev, bio: e.target.value }))
                      setHasChanges(true)
                    }}
                    placeholder="Tell others about yourself..."
                    className="min-h-[100px]"
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="publicProfile"
                    checked={profileSettings.publicProfile}
                    onCheckedChange={(checked) => {
                      setProfileSettings(prev => ({ ...prev, publicProfile: checked }))
                      setHasChanges(true)
                    }}
                  />
                  <Label htmlFor="publicProfile">Make profile public</Label>
                </div>
              </CardContent>
            </Card>
          </div>
        )

      case 'security':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Security Settings</CardTitle>
                <CardDescription>
                  Manage your account security and authentication preferences
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Two-Factor Authentication</Label>
                    <p className="text-sm text-muted-foreground">
                      Add an extra layer of security to your account
                    </p>
                  </div>
                  <Switch
                    checked={securitySettings.twoFactorEnabled}
                    onCheckedChange={(checked) => {
                      setSecuritySettings(prev => ({ ...prev, twoFactorEnabled: checked }))
                      setHasChanges(true)
                    }}
                  />
                </div>

                <Separator />

                <div className="space-y-2">
                  <Label>Session Timeout</Label>
                  <Select
                    value={securitySettings.sessionTimeout}
                    onValueChange={(value) => {
                      setSecuritySettings(prev => ({ ...prev, sessionTimeout: value }))
                      setHasChanges(true)
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1h">1 hour</SelectItem>
                      <SelectItem value="8h">8 hours</SelectItem>
                      <SelectItem value="24h">24 hours</SelectItem>
                      <SelectItem value="7d">7 days</SelectItem>
                      <SelectItem value="never">Never</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="showLastSignIn"
                    checked={securitySettings.showLastSignIn}
                    onCheckedChange={(checked) => {
                      setSecuritySettings(prev => ({ ...prev, showLastSignIn: checked }))
                      setHasChanges(true)
                    }}
                  />
                  <Label htmlFor="showLastSignIn">Show last sign-in information</Label>
                </div>
              </CardContent>
            </Card>
          </div>
        )

      case 'notifications':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
                <CardDescription>
                  Choose how and when you want to be notified
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Email Notifications</Label>
                    <p className="text-sm text-muted-foreground">
                      Receive important updates via email
                    </p>
                  </div>
                  <Switch
                    checked={notificationSettings.emailNotifications}
                    onCheckedChange={(checked) => {
                      setNotificationSettings(prev => ({ ...prev, emailNotifications: checked }))
                      setHasChanges(true)
                    }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Push Notifications</Label>
                    <p className="text-sm text-muted-foreground">
                      Get real-time notifications in your browser
                    </p>
                  </div>
                  <Switch
                    checked={notificationSettings.pushNotifications}
                    onCheckedChange={(checked) => {
                      setNotificationSettings(prev => ({ ...prev, pushNotifications: checked }))
                      setHasChanges(true)
                    }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Project Updates</Label>
                    <p className="text-sm text-muted-foreground">
                      Notifications about your projects and collaborations
                    </p>
                  </div>
                  <Switch
                    checked={notificationSettings.projectUpdates}
                    onCheckedChange={(checked) => {
                      setNotificationSettings(prev => ({ ...prev, projectUpdates: checked }))
                      setHasChanges(true)
                    }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Security Alerts</Label>
                    <p className="text-sm text-muted-foreground">
                      Important security notifications (always enabled)
                    </p>
                  </div>
                  <Switch
                    checked={notificationSettings.securityAlerts}
                    disabled
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        )

      case 'appearance':
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Appearance Settings</CardTitle>
                <CardDescription>
                  Customize the look and feel of your interface
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Theme</Label>
                  <Select
                    value={appearanceSettings.theme}
                    onValueChange={(value) => {
                      setAppearanceSettings(prev => ({ ...prev, theme: value }))
                      setHasChanges(true)
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="light">Light</SelectItem>
                      <SelectItem value="dark">Dark</SelectItem>
                      <SelectItem value="system">System</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Language</Label>
                  <Select
                    value={appearanceSettings.language}
                    onValueChange={(value) => {
                      setAppearanceSettings(prev => ({ ...prev, language: value }))
                      setHasChanges(true)
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="es">Español</SelectItem>
                      <SelectItem value="fr">Français</SelectItem>
                      <SelectItem value="de">Deutsch</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    id="compactMode"
                    checked={appearanceSettings.compactMode}
                    onCheckedChange={(checked) => {
                      setAppearanceSettings(prev => ({ ...prev, compactMode: checked }))
                      setHasChanges(true)
                    }}
                  />
                  <Label htmlFor="compactMode">Compact mode</Label>
                </div>
              </CardContent>
            </Card>
          </div>
        )

      default:
        return null
    }
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
            Back to Profile
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Settings</h1>
            <p className="text-muted-foreground">Manage your account preferences and settings</p>
          </div>
        </div>
        {hasChanges && (
          <Button onClick={handleSave} className="gap-2">
            <FloppyDisk size={16} />
            Save Changes
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Settings Navigation */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <Button
                  key={tab.id}
                  variant={activeTab === tab.id ? 'default' : 'ghost'}
                  className="w-full justify-start gap-2"
                  onClick={() => setActiveTab(tab.id)}
                >
                  <Icon size={16} />
                  {tab.label}
                </Button>
              )
            })}
          </CardContent>
        </Card>

        {/* Settings Content */}
        <div className="lg:col-span-3">
          {renderTabContent()}
        </div>
      </div>
    </motion.div>
  )
}