# OAuth Provider Setup Guide 🔐

This guide will walk you through setting up OAuth applications with GitHub and Google for your GameForge application.

## 🐙 GitHub OAuth Setup

### Step 1: Create GitHub OAuth Application

1. **Go to GitHub Developer Settings**
   - Navigate to: https://github.com/settings/developers
   - Click on "OAuth Apps" in the left sidebar
   - Click "New OAuth App"

2. **Fill in Application Details**
   ```
   Application name: GameForge Development
   Homepage URL: http://localhost:5000
   Application description: GameForge - AI-Powered Game Development Platform
   Authorization callback URL: http://localhost:3001/api/auth/github/callback
   ```

3. **Register the Application**
   - Click "Register application"
   - You'll be taken to your new OAuth app's settings page

4. **Get Your Credentials**
   - Copy the **Client ID** (it's visible immediately)
   - Click "Generate a new client secret"
   - Copy the **Client Secret** (save it immediately - you won't see it again!)

### Step 2: Update Your Backend Environment

Open your `backend/.env` file and update these values:

```env
GITHUB_CLIENT_ID=your_actual_client_id_here
GITHUB_CLIENT_SECRET=your_actual_client_secret_here
```

---

## 🔍 Google OAuth Setup

### Step 1: Create Google Cloud Project (if you don't have one)

1. **Go to Google Cloud Console**
   - Navigate to: https://console.cloud.google.com/
   - Sign in with your Google account

2. **Create New Project**
   - Click the project dropdown at the top
   - Click "New Project"
   - Project name: `gameforge-oauth`
   - Click "Create"

### Step 2: Enable Google+ API

1. **Navigate to APIs & Services**
   - In the Google Cloud Console, go to "APIs & Services" > "Library"
   - Search for "Google+ API"
   - Click on it and click "Enable"

2. **Alternative: Enable Google Identity**
   - You can also search for "Google Identity" or "Google Sign-In"
   - Enable the Google Identity services

### Step 3: Configure OAuth Consent Screen

1. **Go to OAuth Consent Screen**
   - Navigate to "APIs & Services" > "OAuth consent screen"
   - Choose "External" user type (for development)
   - Click "Create"

2. **Fill in Required Information**
   ```
   App name: GameForge
   User support email: your-email@example.com
   App logo: (optional - you can add your GameForge logo)
   App domain: http://localhost:5000
   Developer contact information: your-email@example.com
   ```

3. **Add Scopes**
   - Click "Add or Remove Scopes"
   - Add these scopes:
     - `../auth/userinfo.email`
     - `../auth/userinfo.profile`
   - Click "Update"

4. **Add Test Users** (for development)
   - Add your Gmail address as a test user
   - Click "Save and Continue"

### Step 4: Create OAuth 2.0 Credentials

1. **Go to Credentials**
   - Navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client ID"

2. **Configure OAuth Client**
   ```
   Application type: Web application
   Name: GameForge Web Client
   
   Authorized JavaScript origins:
   - http://localhost:5000
   
   Authorized redirect URIs:
   - http://localhost:3001/api/auth/google/callback
   ```

3. **Create and Get Credentials**
   - Click "Create"
   - Copy the **Client ID** and **Client Secret** from the popup

### Step 5: Update Your Backend Environment

Open your `backend/.env` file and update these values:

```env
GOOGLE_CLIENT_ID=your_actual_google_client_id_here
GOOGLE_CLIENT_SECRET=your_actual_google_client_secret_here
```

---

## 🧪 Testing Your OAuth Setup

### 1. Restart Your Backend Server

After updating your `.env` file:

```bash
cd backend
npm run dev
```

### 2. Test GitHub OAuth

1. Go to: http://localhost:5000/login
2. Click "Continue with GitHub"
3. You should be redirected to GitHub's authorization page
4. Authorize your application
5. You should be redirected back and logged in

### 3. Test Google OAuth

1. Go to: http://localhost:5000/login
2. Click "Continue with Google"
3. You should see Google's sign-in page
4. Sign in with your Google account
5. You should be redirected back and logged in

---

## 🛠️ Troubleshooting

### Common Issues and Solutions

#### GitHub Issues

**Problem**: "The redirect_uri MUST match the registered callback URL"
- **Solution**: Make sure your callback URL is exactly `http://localhost:3001/api/auth/github/callback`

**Problem**: "Bad credentials"
- **Solution**: Double-check your Client ID and Client Secret in the `.env` file

#### Google Issues

**Problem**: "Error 400: redirect_uri_mismatch"
- **Solution**: Ensure redirect URI is exactly `http://localhost:3001/api/auth/google/callback`

**Problem**: "Access blocked: This app's request is invalid"
- **Solution**: Make sure you've configured the OAuth consent screen properly

**Problem**: "Error 403: access_denied"
- **Solution**: Add your email as a test user in the OAuth consent screen

### Debug Steps

1. **Check your `.env` file**:
   ```bash
   cd backend
   cat .env | grep -E "(GITHUB|GOOGLE)"
   ```

2. **Check backend logs**:
   - Look for OAuth-related error messages in your backend terminal

3. **Verify URLs**:
   - Backend OAuth endpoints: `http://localhost:3001/api/auth/github` and `http://localhost:3001/api/auth/google`
   - Frontend callback handler: `http://localhost:5000/auth/callback`

---

## 🚀 Production Setup Notes

When you deploy to production, you'll need to:

1. **Update OAuth Application URLs**:
   - GitHub: Update Homepage URL and Authorization callback URL to your production domain
   - Google: Update Authorized origins and redirect URIs to your production domain

2. **Update Environment Variables**:
   - Set production values for `FRONTEND_URL` in your backend `.env`
   - Update JWT_SECRET and SESSION_SECRET with secure random values

3. **OAuth Consent Screen**:
   - For Google, you may want to verify your app for public use
   - Update app domains to your production domain

---

## 📋 Quick Reference

### Required Environment Variables
```env
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### Callback URLs to Configure
- **GitHub**: `http://localhost:3001/api/auth/github/callback`
- **Google**: `http://localhost:3001/api/auth/google/callback`

### Test URLs
- **Login Page**: `http://localhost:5000/login`
- **GitHub OAuth**: `http://localhost:3001/api/auth/github`
- **Google OAuth**: `http://localhost:3001/api/auth/google`

---

## ✅ Checklist

- [ ] Created GitHub OAuth application
- [ ] Updated GITHUB_CLIENT_ID in .env
- [ ] Updated GITHUB_CLIENT_SECRET in .env
- [ ] Created Google Cloud project
- [ ] Enabled Google+ API or Google Identity
- [ ] Configured OAuth consent screen
- [ ] Created Google OAuth 2.0 credentials
- [ ] Updated GOOGLE_CLIENT_ID in .env
- [ ] Updated GOOGLE_CLIENT_SECRET in .env
- [ ] Restarted backend server
- [ ] Tested GitHub OAuth flow
- [ ] Tested Google OAuth flow

Once you complete these steps, your OAuth integration will be fully functional! 🎉
