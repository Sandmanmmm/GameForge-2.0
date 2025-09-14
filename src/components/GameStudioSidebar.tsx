import { motion, AnimatePresence } from 'framer-motion'
import { NavigationSection, GameProject } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { AuthContext } from '@/contexts/AuthContext'
import { useContext } from 'react'
// Import icons directly to bypass proxy issues
import { House } from '@phosphor-icons/react/dist/csr/House'
import { FolderOpen } from '@phosphor-icons/react/dist/csr/FolderOpen'
import { Book } from '@phosphor-icons/react/dist/csr/Book'
import { Palette } from '@phosphor-icons/react/dist/csr/Palette'
import { GameController } from '@phosphor-icons/react/dist/csr/GameController'
import { Code } from '@phosphor-icons/react/dist/csr/Code'
import { TestTube } from '@phosphor-icons/react/dist/csr/TestTube'
import { MonitorPlay } from '@phosphor-icons/react/dist/csr/MonitorPlay'
import { Rocket } from '@phosphor-icons/react/dist/csr/Rocket'
import { Sparkle } from '@phosphor-icons/react/dist/csr/Sparkle'
import { List } from '@phosphor-icons/react/dist/csr/List'
import { X } from '@phosphor-icons/react/dist/csr/X'
import { SignIn } from '@phosphor-icons/react/dist/csr/SignIn'
import { UserPlus } from '@phosphor-icons/react/dist/csr/UserPlus'
import { User } from '@phosphor-icons/react/dist/csr/User'
import { SignOut } from '@phosphor-icons/react/dist/csr/SignOut'
import { cn } from '@/lib/utils'

interface GameStudioSidebarProps {
  currentSection: string
  onSectionChange: (sectionId: string) => void
  projects?: GameProject[]
  selectedProject?: GameProject | null
  onProjectSelect?: (project: GameProject) => void
  isCollapsed?: boolean
  onToggleCollapse?: () => void
  className?: string
}

const authNavigationSections: NavigationSection[] = [
  {
    id: 'dashboard',
    name: 'Dashboard',
    icon: House,
    path: '/dashboard'
  },
  {
    id: 'projects',
    name: 'My Projects',
    icon: FolderOpen,
    path: '/projects',
    badge: '3'
  },
  {
    id: 'story',
    name: 'Story & Lore',
    icon: Book,
    path: '/story'
  },
  {
    id: 'assets',
    name: 'Assets',
    icon: Palette,
    path: '/assets'
  },
  {
    id: 'gameplay',
    name: 'Gameplay & Levels',
    icon: GameController,
    path: '/gameplay'
  },
  {
    id: 'code',
    name: 'Code Generation',
    icon: Code,
    path: '/code'
  },
  {
    id: 'qa',
    name: 'QA & Testing',
    icon: TestTube,
    path: '/qa'
  },
  {
    id: 'preview',
    name: 'Preview',
    icon: MonitorPlay,
    path: '/preview'
  },
  {
    id: 'publishing',
    name: 'Publishing',
    icon: Rocket,
    path: '/publishing'
  },
  {
    id: 'creation-test',
    name: '🧪 Enhanced Creation',
    icon: Sparkle,
    path: '/creation-test'
  }
]

const publicNavigationSections: NavigationSection[] = [
  {
    id: 'dashboard',
    name: 'Dashboard',
    icon: House,
    path: '/dashboard'
  },
  {
    id: 'login',
    name: 'Login',
    icon: SignIn,
    path: '/login'
  },
  {
    id: 'register',
    name: 'Register',
    icon: UserPlus,
    path: '/register'
  }
]

export function GameStudioSidebar({
  currentSection,
  onSectionChange,
  projects = [],
  selectedProject,
  onProjectSelect,
  isCollapsed = false,
  onToggleCollapse,
  className
}: GameStudioSidebarProps) {
  const { user, logout } = useContext(AuthContext)
  const navigationSections = user ? authNavigationSections : publicNavigationSections

  return (
    <motion.div
      animate={{ width: isCollapsed ? 80 : 280 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className={cn(
        'h-full bg-card/50 backdrop-blur-sm border-r border-border/50 flex flex-col',
        className
      )}
    >
      {/* Header */}
      <div className="p-6 border-b border-border/30">
        <div className="flex items-center justify-between">
          <AnimatePresence mode="wait">
            {!isCollapsed && (
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
                className="flex items-center gap-3"
              >
                <div className="w-10 h-10 rounded-xl gradient-cosmic flex items-center justify-center">
                  <Sparkle size={24} className="text-white" />
                </div>
                <div>
                  <h1 className="font-bold text-xl text-foreground">GameForge</h1>
                  <p className="text-xs text-muted-foreground">AI Game Studio</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggleCollapse}
            className="text-muted-foreground hover:text-foreground shrink-0"
          >
            {isCollapsed ? <List size={20} /> : <X size={20} />}
          </Button>
        </div>
      </div>

      {/* Navigation */}
      <ScrollArea className="flex-1 p-4 custom-scrollbar">
        {/* Project Selector */}
        <AnimatePresence>
          {!isCollapsed && user && projects.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              className="mb-4"
            >
              <div className="px-2 pb-2">
                <p className="text-xs font-medium text-muted-foreground mb-2">Current Project</p>
                <Select 
                  value={selectedProject?.id || ""} 
                  onValueChange={(projectId) => {
                    const project = projects.find(p => p.id === projectId)
                    if (project && onProjectSelect) {
                      onProjectSelect(project)
                    }
                  }}
                >
                  <SelectTrigger className="w-full h-9 text-sm">
                    <SelectValue placeholder="Select a project..." />
                  </SelectTrigger>
                  <SelectContent>
                    {projects.map((project) => (
                      <SelectItem key={project.id} value={project.id}>
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${
                            project.status === 'complete' ? 'bg-green-500' :
                            project.status === 'development' ? 'bg-blue-500' :
                            project.status === 'testing' ? 'bg-yellow-500' :
                            'bg-gray-500'
                          }`} />
                          <span className="truncate">{project.title}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Separator className="mb-4 bg-border/30" />
            </motion.div>
          )}
        </AnimatePresence>

        <nav className="space-y-2">
          {navigationSections.map((section, index) => {
            const Icon = section.icon
            const isActive = currentSection === section.id
            
            return (
              <motion.div
                key={section.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05, duration: 0.3 }}
              >
                <Button
                  variant={isActive ? "secondary" : "ghost"}
                  onClick={() => onSectionChange(section.id)}
                  className={cn(
                    'w-full justify-start gap-3 h-11 transition-all duration-200',
                    isActive && 'bg-accent/20 text-accent border border-accent/30 glow-gold',
                    !isActive && 'hover:bg-muted/50 hover:text-foreground',
                    isCollapsed && 'justify-center px-0'
                  )}
                >
                  <Icon size={20} className="shrink-0" />
                  
                  <AnimatePresence mode="wait">
                    {!isCollapsed && (
                      <motion.div
                        initial={{ opacity: 0, width: 0 }}
                        animate={{ opacity: 1, width: 'auto' }}
                        exit={{ opacity: 0, width: 0 }}
                        transition={{ duration: 0.2 }}
                        className="flex items-center justify-between flex-1 overflow-hidden"
                      >
                        <span className="font-medium truncate">{section.name}</span>
                        {section.badge && (
                          <Badge 
                            variant="secondary" 
                            className="ml-2 bg-accent/20 text-accent text-xs shrink-0"
                          >
                            {section.badge}
                          </Badge>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </Button>
              </motion.div>
            )
          })}
        </nav>

        <AnimatePresence>
          {!isCollapsed && user && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              transition={{ delay: 0.3, duration: 0.3 }}
              className="mt-8"
            >
              <Separator className="mb-4 bg-border/30" />
              
              {/* Quick Stats */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-muted-foreground px-2">Quick Stats</h4>
                <div className="grid grid-cols-2 gap-2">
                  <div className="glass p-3 rounded-lg text-center">
                    <div className="text-lg font-bold text-accent">3</div>
                    <div className="text-xs text-muted-foreground">Active Projects</div>
                  </div>
                  <div className="glass p-3 rounded-lg text-center">
                    <div className="text-lg font-bold text-emerald-400">67%</div>
                    <div className="text-xs text-muted-foreground">Avg Progress</div>
                  </div>
                </div>
              </div>

              {/* Recent Activity removed to make space for account management icons */}
            </motion.div>
          )}
        </AnimatePresence>
      </ScrollArea>

      {/* Footer */}
      <div className="p-4 border-t border-border/30">
        {/* User Profile Section for Authenticated Users */}
        {user && (
          <AnimatePresence>
            {!isCollapsed && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                transition={{ duration: 0.2 }}
                className="mb-4"
              >
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button 
                      variant="ghost" 
                      className="w-full justify-start gap-3 p-3 h-auto hover:bg-muted/50"
                    >
                      <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center">
                        <User size={16} className="text-accent" />
                      </div>
                      <div className="flex-1 text-left">
                        <div className="text-sm font-medium truncate">{user.name || 'User'}</div>
                        <div className="text-xs text-muted-foreground truncate">{user.email}</div>
                      </div>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start" className="w-56">
                    <DropdownMenuItem onClick={() => onSectionChange('profile')}>
                      <User className="mr-2 h-4 w-4" />
                      <span>Profile</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={logout} className="text-red-600">
                      <SignOut className="mr-2 h-4 w-4" />
                      <span>Logout</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </motion.div>
            )}
          </AnimatePresence>
        )}

        <AnimatePresence>
          {!isCollapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="text-center"
            >
              <div className="text-xs text-muted-foreground mb-2">
                Powered by AI
              </div>
              <div className="flex items-center justify-center gap-1">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs text-emerald-400 font-medium">System Online</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}