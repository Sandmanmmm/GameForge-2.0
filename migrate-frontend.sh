#!/bin/bash

# GameForge Frontend Migration Script
# Production-Ready Customer-Facing System Migration
# ================================================

set -e  # Exit on any error

echo "🚀 Starting GameForge Frontend Migration to Production-Ready System"
echo "=================================================================="

# Configuration
SOURCE_DIR="."
TARGET_REPO="https://github.com/Sandmanmmm/GameForge_Frontend.git"
TEMP_DIR="./migration_temp"
FRONTEND_DIR="$TEMP_DIR/GameForge_Frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Prepare migration environment
print_status "Step 1: Preparing migration environment..."
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# Step 2: Clone target repository
print_status "Step 2: Cloning target frontend repository..."
cd "$TEMP_DIR"
git clone "$TARGET_REPO"
cd GameForge_Frontend

# Initialize if empty repository
if [ ! -f "package.json" ]; then
    print_status "Initializing empty repository..."
    npm init -y
fi

cd ../..

# Step 3: Copy core configuration files
print_status "Step 3: Copying core configuration files..."

# Package.json with production dependencies
cat > "$FRONTEND_DIR/package.json" << 'EOF'
{
  "name": "gameforge-frontend",
  "version": "1.0.0",
  "description": "GameForge AI Game Asset Generator - Customer Frontend",
  "type": "module",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "build:staging": "tsc -b && vite build --mode staging",
    "build:production": "tsc -b && vite build --mode production",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "lint:fix": "eslint . --ext ts,tsx --fix",
    "preview": "vite preview",
    "type-check": "tsc --noEmit",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "coverage": "vitest run --coverage",
    "analyze": "npx vite-bundle-analyzer"
  },
  "dependencies": {
    "@github/spark": "^0.39.0",
    "@heroicons/react": "^2.2.0",
    "@hookform/resolvers": "^4.1.3",
    "@phosphor-icons/react": "^2.1.7",
    "@radix-ui/colors": "^3.0.0",
    "@radix-ui/react-accordion": "^1.2.3",
    "@radix-ui/react-alert-dialog": "^1.1.6",
    "@radix-ui/react-aspect-ratio": "^1.1.2",
    "@radix-ui/react-avatar": "^1.1.3",
    "@radix-ui/react-checkbox": "^1.1.4",
    "@radix-ui/react-collapsible": "^1.1.3",
    "@radix-ui/react-context-menu": "^2.2.6",
    "@radix-ui/react-dialog": "^1.1.6",
    "@radix-ui/react-dropdown-menu": "^2.1.6",
    "@radix-ui/react-hover-card": "^1.1.6",
    "@radix-ui/react-label": "^2.1.2",
    "@radix-ui/react-menubar": "^1.1.6",
    "@radix-ui/react-navigation-menu": "^1.2.5",
    "@radix-ui/react-popover": "^1.1.6",
    "@radix-ui/react-progress": "^1.1.2",
    "@radix-ui/react-radio-group": "^1.2.3",
    "@radix-ui/react-scroll-area": "^1.2.9",
    "@radix-ui/react-select": "^2.1.6",
    "@radix-ui/react-separator": "^1.1.2",
    "@radix-ui/react-slider": "^1.2.3",
    "@radix-ui/react-slot": "^1.1.2",
    "@radix-ui/react-switch": "^1.1.3",
    "@radix-ui/react-tabs": "^1.1.3",
    "@radix-ui/react-toggle": "^1.1.2",
    "@radix-ui/react-toggle-group": "^1.1.2",
    "@radix-ui/react-tooltip": "^1.1.8",
    "@sentry/react": "^7.118.0",
    "@sentry/tracing": "^7.118.0",
    "@tailwindcss/container-queries": "^0.1.1",
    "@tailwindcss/vite": "^4.1.11",
    "@tanstack/react-query": "^5.83.1",
    "axios": "^1.11.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "cmdk": "^1.1.1",
    "d3": "^7.9.0",
    "date-fns": "^3.6.0",
    "embla-carousel-react": "^8.5.2",
    "framer-motion": "^12.6.2",
    "input-otp": "^1.4.2",
    "lucide-react": "^0.484.0",
    "marked": "^15.0.7",
    "next-themes": "^0.4.6",
    "react": "^19.0.0",
    "react-day-picker": "^9.6.7",
    "react-dom": "^19.0.0",
    "react-error-boundary": "^6.0.0",
    "react-hook-form": "^7.54.2",
    "react-resizable-panels": "^2.1.7",
    "react-router-dom": "^7.8.2",
    "recharts": "^2.15.1",
    "sonner": "^2.0.1",
    "tailwind-merge": "^3.0.2",
    "three": "^0.175.0",
    "uuid": "^11.1.0",
    "vaul": "^1.1.2",
    "zod": "^3.25.76"
  },
  "devDependencies": {
    "@eslint/js": "^9.21.0",
    "@tailwindcss/postcss": "^4.1.8",
    "@types/react": "^19.1.12",
    "@types/react-dom": "^19.0.4",
    "@types/three": "^0.175.0",
    "@types/uuid": "^11.1.0",
    "@vitejs/plugin-react-swc": "^3.10.1",
    "@vitest/ui": "^1.6.0",
    "eslint": "^9.28.0",
    "eslint-plugin-react-hooks": "^5.2.0",
    "eslint-plugin-react-refresh": "^0.4.19",
    "globals": "^16.0.0",
    "tailwindcss": "^4.1.11",
    "typescript": "~5.7.2",
    "typescript-eslint": "^8.38.0",
    "vite": "^6.3.5",
    "vite-bundle-analyzer": "^0.7.0",
    "vitest": "^1.6.0"
  },
  "engines": {
    "node": ">=18.0.0",
    "npm": ">=8.0.0"
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
EOF

# Copy all critical frontend files
print_status "Step 4: Copying frontend source files..."

# Copy source directory
cp -r "$SOURCE_DIR/src" "$FRONTEND_DIR/"

# Copy configuration files
cp "$SOURCE_DIR/vite.config.ts" "$FRONTEND_DIR/"
cp "$SOURCE_DIR/tailwind.config.js" "$FRONTEND_DIR/"
cp "$SOURCE_DIR/components.json" "$FRONTEND_DIR/"
cp "$SOURCE_DIR/index.html" "$FRONTEND_DIR/"

# Copy environment files
cp "$SOURCE_DIR/.env.production" "$FRONTEND_DIR/"
cp "$SOURCE_DIR/.env.development" "$FRONTEND_DIR/"
cp "$SOURCE_DIR/.env.staging" "$FRONTEND_DIR/"

# Create TypeScript configuration
cat > "$FRONTEND_DIR/tsconfig.json" << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
EOF

cat > "$FRONTEND_DIR/tsconfig.node.json" << 'EOF'
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
EOF

# Create production-ready Vite config
cat > "$FRONTEND_DIR/vite.config.ts" << 'EOF'
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react-swc";
import { defineConfig, loadEnv } from "vite";
import { resolve } from 'path';

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  
  return {
    plugins: [
      react(),
      tailwindcss()
    ],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    build: {
      outDir: 'dist',
      sourcemap: mode !== 'production',
      minify: mode === 'production' ? 'esbuild' : false,
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['react', 'react-dom'],
            ui: [
              '@radix-ui/react-dialog', 
              '@radix-ui/react-dropdown-menu',
              '@radix-ui/react-tabs'
            ],
            utils: ['clsx', 'class-variance-authority', 'tailwind-merge']
          }
        }
      },
      chunkSizeWarningLimit: 1000
    },
    server: {
      port: 3000,
      proxy: mode === 'development' ? {
        '/api': {
          target: env.VITE_GAMEFORGE_API_URL || 'http://localhost:8080',
          changeOrigin: true,
          secure: false
        }
      } : undefined
    },
    preview: {
      port: 3000
    },
    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0'),
      __BUILD_TIME__: JSON.stringify(new Date().toISOString())
    }
  };
});
EOF

# Step 5: Create deployment configurations
print_status "Step 5: Creating deployment configurations..."

# Vercel configuration
cat > "$FRONTEND_DIR/vercel.json" << 'EOF'
{
  "framework": "vite",
  "buildCommand": "npm run build:production",
  "outputDirectory": "dist",
  "installCommand": "npm ci",
  "devCommand": "npm run dev",
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://api.gameforge.app/api/$1"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-XSS-Protection",
          "value": "1; mode=block"
        },
        {
          "key": "Referrer-Policy",
          "value": "strict-origin-when-cross-origin"
        },
        {
          "key": "Permissions-Policy",
          "value": "camera=(), microphone=(), geolocation=()"
        }
      ]
    },
    {
      "source": "/assets/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
EOF

# Netlify configuration
cat > "$FRONTEND_DIR/netlify.toml" << 'EOF'
[build]
  command = "npm run build:production"
  publish = "dist"

[build.environment]
  NODE_VERSION = "18"

[[redirects]]
  from = "/api/*"
  to = "https://api.gameforge.app/api/:splat"
  status = 200
  force = true

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-XSS-Protection = "1; mode=block"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
    Permissions-Policy = "camera=(), microphone=(), geolocation=()"

[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
EOF

# Docker configuration for self-hosting
cat > "$FRONTEND_DIR/Dockerfile" << 'EOF'
# Multi-stage build for production
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy source code
COPY . .

# Build the application
RUN npm run build:production

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Add security headers
RUN echo 'add_header X-Frame-Options "DENY" always;' > /etc/nginx/conf.d/security.conf && \
    echo 'add_header X-Content-Type-Options "nosniff" always;' >> /etc/nginx/conf.d/security.conf && \
    echo 'add_header X-XSS-Protection "1; mode=block" always;' >> /etc/nginx/conf.d/security.conf && \
    echo 'add_header Referrer-Policy "strict-origin-when-cross-origin" always;' >> /etc/nginx/conf.d/security.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
EOF

# Nginx configuration
cat > "$FRONTEND_DIR/nginx.conf" << 'EOF'
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Security headers
    include /etc/nginx/conf.d/security.conf;
    
    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    server {
        listen 80;
        server_name _;
        root /usr/share/nginx/html;
        index index.html;
        
        # Security
        server_tokens off;
        
        # Cache static assets
        location /assets/ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
        
        # API proxy
        location /api/ {
            proxy_pass https://api.gameforge.app/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # SPA fallback
        location / {
            try_files $uri $uri/ /index.html;
        }
        
        # Health check
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
EOF

# Step 6: Copy CI/CD workflows
print_status "Step 6: Setting up CI/CD workflows..."
mkdir -p "$FRONTEND_DIR/.github/workflows"
cp "$SOURCE_DIR/.github/workflows/frontend-cicd.yml" "$FRONTEND_DIR/.github/workflows/ci-cd.yml"

# Step 7: Create security and monitoring setup
print_status "Step 7: Setting up security and monitoring..."

# Copy monitoring service
cp "$SOURCE_DIR/src/services/monitoring.ts" "$FRONTEND_DIR/src/services/"
cp "$SOURCE_DIR/src/services/secureAuth.ts" "$FRONTEND_DIR/src/services/"

# Create security configuration
cat > "$FRONTEND_DIR/src/config/security.ts" << 'EOF'
/**
 * Security Configuration for Production
 */

export const securityConfig = {
  // Content Security Policy
  csp: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'", "'unsafe-inline'", "https://app.posthog.com"],
    styleSrc: ["'self'", "'unsafe-inline'"],
    imgSrc: ["'self'", "data:", "https:", "blob:"],
    connectSrc: [
      "'self'", 
      "https://api.gameforge.app",
      "https://app.posthog.com",
      "https://sentry.io"
    ],
    fontSrc: ["'self'", "data:"],
    objectSrc: ["'none'"],
    mediaSrc: ["'self'", "blob:"],
    frameSrc: ["'none'"]
  },
  
  // Rate limiting (client-side hints)
  rateLimits: {
    apiCalls: 100, // per minute
    uploads: 10,   // per minute
    login: 5       // per minute
  },
  
  // File upload restrictions
  fileUpload: {
    maxSize: 10 * 1024 * 1024, // 10MB
    allowedTypes: [
      'image/jpeg',
      'image/png', 
      'image/webp',
      'audio/mpeg',
      'audio/wav',
      'model/gltf+json',
      'model/gltf-binary'
    ]
  },
  
  // HTTPS enforcement
  enforceHttps: process.env.NODE_ENV === 'production',
  
  // API security
  api: {
    timeout: 30000, // 30 seconds
    retries: 3,
    csrfProtection: true
  }
};
EOF

# Step 8: Create production README
print_status "Step 8: Creating production documentation..."

cat > "$FRONTEND_DIR/README.md" << 'EOF'
# GameForge Frontend - Customer-Facing Application

A production-ready React application for GameForge AI game asset generation platform.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build:production

# Preview production build
npm run preview
```

## 🏗️ Build Commands

- `npm run dev` - Development server
- `npm run build` - Production build
- `npm run build:staging` - Staging build  
- `npm run build:production` - Production build with optimizations
- `npm run preview` - Preview production build locally

## 🔧 Environment Configuration

### Development (.env.development)
```bash
VITE_GAMEFORGE_API_URL=http://localhost:8080/api/v1
VITE_NODE_ENV=development
VITE_ENABLE_DEBUG_MODE=true
```

### Production (.env.production)
```bash
VITE_GAMEFORGE_API_URL=https://api.gameforge.app/api/v1
VITE_NODE_ENV=production
VITE_ENABLE_ANALYTICS=true
VITE_SENTRY_DSN=your_sentry_dsn
```

## 🚀 Deployment

### Vercel (Recommended)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

### Netlify
```bash
# Install Netlify CLI
npm i -g netlify-cli

# Deploy
netlify deploy --prod --dir=dist
```

### Docker
```bash
# Build image
docker build -t gameforge-frontend .

# Run container
docker run -p 80:80 gameforge-frontend
```

## 🔒 Security Features

- ✅ Secure authentication with client-side token management
- ✅ CORS configuration for production domains
- ✅ Content Security Policy (CSP) headers
- ✅ XSS protection
- ✅ CSRF protection
- ✅ Secure file upload handling
- ✅ Rate limiting hints
- ✅ HTTPS enforcement

## 📊 Monitoring & Analytics

- **Error Tracking**: Sentry integration
- **Performance**: Web Vitals monitoring
- **User Analytics**: PostHog integration
- **Health Checks**: `/health` endpoint

## 🧪 Testing

```bash
# Run tests
npm run test

# Run tests with UI
npm run test:ui

# Coverage report
npm run coverage
```

## 📦 Dependencies

### Core
- React 19 with TypeScript
- Vite for build tooling
- TailwindCSS for styling
- React Router for navigation

### UI Components
- Radix UI primitives
- Framer Motion animations
- Lucide React icons

### Security & Monitoring
- Sentry for error tracking
- Secure authentication service
- Environment-based configuration

## 🔄 API Communication

The frontend communicates with the GameForge backend through secure REST APIs:

- **Authentication**: JWT-based with refresh tokens
- **API Base**: Configurable via environment variables
- **CORS**: Properly configured for cross-origin requests
- **Error Handling**: Comprehensive error boundaries

## 📱 Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is proprietary software owned by GameForge.
EOF

# Step 9: Create git configuration
print_status "Step 9: Setting up git configuration..."

cat > "$FRONTEND_DIR/.gitignore" << 'EOF'
# Dependencies
node_modules/
.pnp
.pnp.js

# Production builds
/dist
/build

# Environment files
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Logs
npm-debug.log*
yarn-debug.log*
yarn-error.log*
lerna-debug.log*

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/
*.lcov

# Dependency directories
.npm
.eslintcache

# Optional npm cache directory
.npm

# Microbundle cache
.rpt2_cache/
.rts2_cache_cjs/
.rts2_cache_es/
.rts2_cache_umd/

# Optional REPL history
.node_repl_history

# Output of 'npm pack'
*.tgz

# Yarn Integrity file
.yarn-integrity

# parcel-bundler cache (https://parceljs.org/)
.cache
.parcel-cache

# Storybook build outputs
.out
.storybook-out

# Temporary folders
tmp/
temp/

# Editor directories and files
.vscode/*
!.vscode/extensions.json
.idea
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?

# Local Netlify folder
.netlify

# Vercel
.vercel
EOF

# Step 10: Initialize git and commit
print_status "Step 10: Initializing git repository..."
cd "$FRONTEND_DIR"

git init
git add .
git commit -m "Initial commit: Production-ready GameForge frontend

Features:
- Secure authentication with client-side token management
- Production CORS configuration
- Sentry error tracking and monitoring
- Comprehensive CI/CD pipeline
- Multiple deployment options (Vercel, Netlify, Docker)
- Security headers and CSP
- Performance optimizations
- TypeScript with strict mode
- Comprehensive testing setup"

# Step 11: Set up remote and push
print_status "Step 11: Pushing to remote repository..."
git branch -M main
git remote add origin "$TARGET_REPO"
git push -u origin main

cd ../..

# Step 12: Cleanup
print_status "Step 12: Cleaning up..."
rm -rf "$TEMP_DIR"

print_success "🎉 Migration completed successfully!"
echo ""
echo "Next steps:"
echo "1. Visit: https://github.com/Sandmanmmm/GameForge_Frontend"
echo "2. Set up deployment secrets in repository settings"
echo "3. Configure environment variables for production"
echo "4. Set up monitoring dashboards"
echo "5. Deploy to your chosen platform"
echo ""
echo "Repository structure:"
echo "- ✅ Production-ready React frontend"
echo "- ✅ Secure authentication system"
echo "- ✅ CI/CD pipeline configured"
echo "- ✅ Multiple deployment options"
echo "- ✅ Security and monitoring setup"
echo "- ✅ Comprehensive documentation"
EOF