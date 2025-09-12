# 🔐 OAuth Authentication Integration Plan
## GitHub + Google Login for GameForge

## 📋 **Analysis & Implementation Strategy**

### **Current Authentication System**
✅ **Already Implemented:**
- JWT-based authentication with 7-day expiry
- BCrypt password hashing
- User registration/login endpoints
- Protected routes with middleware
- Frontend AuthContext with persistent sessions

### **OAuth Integration Approach**
We'll implement **OAuth 2.0** with **Passport.js** for both GitHub and Google, maintaining compatibility with existing email/password authentication.

---

## 🏗️ **Backend Implementation Plan**

### **1. Install Required Dependencies**
```bash
cd backend
npm install passport passport-github2 passport-google-oauth20 passport-jwt express-session
npm install @types/passport @types/passport-github2 @types/passport-google-oauth20 @types/express-session --save-dev
```

### **2. Database Schema Updates**
Update Prisma schema to support OAuth providers:

```prisma
model User {
  id          String    @id @default(cuid())
  email       String    @unique
  password    String?   # Make optional for OAuth users
  name        String?
  avatar      String?   # Profile image from OAuth
  
  // OAuth fields
  githubId    String?   @unique
  googleId    String?   @unique
  provider    String[]  @default(["email"]) # Track auth methods
  
  projects    Project[]
  createdAt   DateTime  @default(now())
  updatedAt   DateTime  @updatedAt
  
  @@map("users")
}
```

### **3. OAuth Configuration**
Add to `.env`:
```env
# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# Google OAuth  
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Session secret
SESSION_SECRET=your_session_secret_key
```

### **4. Passport Strategy Setup**
Create `src/config/passport.ts`:

```typescript
import passport from 'passport';
import { Strategy as GitHubStrategy } from 'passport-github2';
import { Strategy as GoogleStrategy } from 'passport-google-oauth20';
import { Strategy as JwtStrategy, ExtractJwt } from 'passport-jwt';
import { PrismaClient } from '@prisma/client';
import { config } from './index';

const prisma = new PrismaClient();

// GitHub Strategy
passport.use(new GitHubStrategy({
  clientID: config.githubClientId,
  clientSecret: config.githubClientSecret,
  callbackURL: "/api/auth/github/callback"
}, async (accessToken, refreshToken, profile, done) => {
  try {
    let user = await prisma.user.findUnique({
      where: { githubId: profile.id }
    });

    if (!user) {
      // Check if user exists with same email
      const existingUser = await prisma.user.findUnique({
        where: { email: profile.emails?.[0]?.value }
      });

      if (existingUser) {
        // Link GitHub to existing account
        user = await prisma.user.update({
          where: { id: existingUser.id },
          data: {
            githubId: profile.id,
            provider: [...existingUser.provider, 'github'],
            avatar: profile.photos?.[0]?.value
          }
        });
      } else {
        // Create new user
        user = await prisma.user.create({
          data: {
            githubId: profile.id,
            email: profile.emails?.[0]?.value || `github_${profile.id}@gameforge.local`,
            name: profile.displayName || profile.username,
            avatar: profile.photos?.[0]?.value,
            provider: ['github']
          }
        });
      }
    }

    return done(null, user);
  } catch (error) {
    return done(error, null);
  }
}));

// Google Strategy
passport.use(new GoogleStrategy({
  clientID: config.googleClientId,
  clientSecret: config.googleClientSecret,
  callbackURL: "/api/auth/google/callback"
}, async (accessToken, refreshToken, profile, done) => {
  try {
    let user = await prisma.user.findUnique({
      where: { googleId: profile.id }
    });

    if (!user) {
      const existingUser = await prisma.user.findUnique({
        where: { email: profile.emails?.[0]?.value }
      });

      if (existingUser) {
        user = await prisma.user.update({
          where: { id: existingUser.id },
          data: {
            googleId: profile.id,
            provider: [...existingUser.provider, 'google'],
            avatar: profile.photos?.[0]?.value
          }
        });
      } else {
        user = await prisma.user.create({
          data: {
            googleId: profile.id,
            email: profile.emails?.[0]?.value || `google_${profile.id}@gameforge.local`,
            name: profile.displayName,
            avatar: profile.photos?.[0]?.value,
            provider: ['google']
          }
        });
      }
    }

    return done(null, user);
  } catch (error) {
    return done(error, null);
  }
}));
```

### **5. OAuth Routes**
Create `src/routes/oauth.ts`:

```typescript
import express from 'express';
import passport from 'passport';
import jwt from 'jsonwebtoken';
import { config } from '../config';

const router = express.Router();

// GitHub OAuth routes
router.get('/github', 
  passport.authenticate('github', { scope: ['user:email'] })
);

router.get('/github/callback',
  passport.authenticate('github', { session: false }),
  (req, res) => {
    const token = jwt.sign(
      { userId: req.user.id, email: req.user.email },
      config.jwtSecret,
      { expiresIn: '7d' }
    );

    // Redirect to frontend with token
    res.redirect(`${config.frontendUrl}/auth/success?token=${token}`);
  }
);

// Google OAuth routes
router.get('/google',
  passport.authenticate('google', { scope: ['profile', 'email'] })
);

router.get('/google/callback',
  passport.authenticate('google', { session: false }),
  (req, res) => {
    const token = jwt.sign(
      { userId: req.user.id, email: req.user.email },
      config.jwtSecret,
      { expiresIn: '7d' }
    );

    res.redirect(`${config.frontendUrl}/auth/success?token=${token}`);
  }
);

export default router;
```

---

## 🎨 **Frontend Implementation Plan**

### **1. OAuth Login Buttons**
Update `LoginPage.tsx`:

```tsx
import React, { useState, useContext } from "react";
import { AuthContext } from "../contexts/AuthContext";

export default function LoginPage() {
  const { login } = useContext(AuthContext);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login(email, password);
      window.location.href = "/dashboard";
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleOAuthLogin = (provider: 'github' | 'google') => {
    window.location.href = `http://localhost:3001/api/auth/${provider}`;
  };

  return (
    <div className="flex items-center justify-center h-screen bg-gray-50">
      <div className="bg-white p-8 rounded-2xl shadow-lg w-96">
        <h1 className="text-2xl font-bold mb-6 text-center">Login to GameForge</h1>
        
        {/* OAuth Buttons */}
        <div className="space-y-3 mb-6">
          <button
            onClick={() => handleOAuthLogin('github')}
            className="w-full bg-gray-900 text-white p-3 rounded-xl hover:bg-gray-800 transition flex items-center justify-center gap-2"
          >
            <GitHubIcon className="w-5 h-5" />
            Continue with GitHub
          </button>
          
          <button
            onClick={() => handleOAuthLogin('google')}
            className="w-full bg-red-500 text-white p-3 rounded-xl hover:bg-red-600 transition flex items-center justify-center gap-2"
          >
            <GoogleIcon className="w-5 h-5" />
            Continue with Google
          </button>
        </div>

        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">Or continue with email</span>
          </div>
        </div>

        {/* Email/Password Form */}
        {error && <p className="text-red-500 mb-3">{error}</p>}
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            className="w-full p-3 mb-3 border rounded-xl"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            className="w-full p-3 mb-6 border rounded-xl"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button className="w-full bg-indigo-600 text-white p-3 rounded-xl hover:bg-indigo-700 transition">
            Login with Email
          </button>
        </form>
      </div>
    </div>
  );
}
```

### **2. OAuth Success Handler**
Create `src/components/AuthSuccess.tsx`:

```tsx
import React, { useEffect, useContext } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';

export default function AuthSuccess() {
  const [searchParams] = useSearchParams();
  const { setAuthFromToken } = useContext(AuthContext);

  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      setAuthFromToken(token);
      window.location.href = '/dashboard';
    }
  }, [searchParams, setAuthFromToken]);

  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Completing authentication...</p>
      </div>
    </div>
  );
}
```

### **3. Update AuthContext**
Add OAuth support to `AuthContext.tsx`:

```tsx
interface AuthContextType {
  user: any;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  setAuthFromToken: (token: string) => Promise<void>;
  logout: () => void;
}

// Add method to AuthProvider
const setAuthFromToken = async (token: string) => {
  try {
    const res = await fetch("http://localhost:3001/api/auth/profile", {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    if (res.ok) {
      const userData = await res.json();
      setToken(token);
      setUser(userData.user);
      localStorage.setItem("token", token);
      localStorage.setItem("user", JSON.stringify(userData.user));
    }
  } catch (error) {
    console.error('OAuth authentication failed:', error);
  }
};
```

---

## 🚀 **Implementation Steps**

### **Phase 1: Setup OAuth Apps**
1. **GitHub**: Create OAuth App at https://github.com/settings/developers
   - Homepage URL: `http://localhost:5000`
   - Callback URL: `http://localhost:3001/api/auth/github/callback`

2. **Google**: Create OAuth 2.0 Client at https://console.developers.google.com
   - Authorized origins: `http://localhost:3001`
   - Redirect URIs: `http://localhost:3001/api/auth/google/callback`

### **Phase 2: Backend Integration**
1. Install dependencies
2. Update database schema
3. Configure Passport strategies
4. Add OAuth routes
5. Update environment variables

### **Phase 3: Frontend Integration**
1. Update login page with OAuth buttons
2. Add OAuth success handler
3. Update AuthContext for OAuth
4. Add OAuth callback route

### **Phase 4: Testing**
1. Test GitHub OAuth flow
2. Test Google OAuth flow
3. Test account linking
4. Verify existing email/password still works

---

## 🔧 **Benefits**

✅ **Better UX**: One-click social login  
✅ **Security**: OAuth 2.0 standard  
✅ **Account Linking**: Connect multiple providers  
✅ **Profile Data**: Auto-populate user info  
✅ **Backward Compatible**: Email/password still works  

Would you like me to start implementing any specific part of this OAuth integration?
