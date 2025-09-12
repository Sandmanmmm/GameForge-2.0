# 🔐 OAuth Provider Setup Assistant

## Current Status: ⚠️ OAuth Credentials Needed

Your GameForge application is ready for OAuth integration, but you need to set up the actual OAuth applications with GitHub and Google to get the required credentials.

---

## 🐙 **STEP 1: GitHub OAuth Setup**

### A. Create GitHub OAuth Application

1. **Open GitHub Developer Settings**
   - Go to: https://github.com/settings/developers
   - Click "OAuth Apps" → "New OAuth App"

2. **Fill out the form with these exact values:**
   ```
   Application name: GameForge Development
   Homepage URL: http://localhost:5000
   Application description: GameForge - AI-Powered Game Development Platform
   Authorization callback URL: http://localhost:3001/api/auth/github/callback
   ```
   ⚠️ **Important**: The callback URL must be exactly `http://localhost:3001/api/auth/github/callback`

3. **Click "Register application"**

4. **Copy your credentials:**
   - Copy the **Client ID** (visible immediately)
   - Click "Generate a new client secret" 
   - Copy the **Client Secret** (save it now - you won't see it again!)

### B. Update Your Configuration

Open `backend/.env` and replace these lines:
```env
GITHUB_CLIENT_ID=your_actual_client_id_here
GITHUB_CLIENT_SECRET=your_actual_client_secret_here
```

---

## 🔍 **STEP 2: Google OAuth Setup**

### A. Create Google Cloud Project

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/
   - Sign in with your Google account

2. **Create a new project:**
   - Click the project dropdown at the top
   - Click "New Project"
   - Name: `gameforge-oauth`
   - Click "Create"

### B. Configure OAuth Consent Screen

1. **Navigate to OAuth consent screen:**
   - Go to "APIs & Services" → "OAuth consent screen"
   - Select "External" → Click "Create"

2. **Fill in required information:**
   ```
   App name: GameForge
   User support email: [your-email@example.com]
   Developer contact information: [your-email@example.com]
   ```

3. **Add your email as a test user:**
   - In the "Test users" section, add your Gmail address
   - Click "Save and Continue"

### C. Create OAuth 2.0 Credentials

1. **Go to Credentials:**
   - Navigate to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth 2.0 Client ID"

2. **Configure the client:**
   ```
   Application type: Web application
   Name: GameForge Web Client
   
   Authorized redirect URIs:
   http://localhost:3001/api/auth/google/callback
   ```
   ⚠️ **Important**: The redirect URI must be exactly `http://localhost:3001/api/auth/google/callback`

3. **Click "Create" and copy your credentials**

### D. Update Your Configuration

Open `backend/.env` and replace these lines:
```env
GOOGLE_CLIENT_ID=your_actual_google_client_id_here
GOOGLE_CLIENT_SECRET=your_actual_google_client_secret_here
```

---

## ✅ **STEP 3: Test Your Setup**

### A. Restart Your Backend Server

```bash
cd backend
npm run dev
```

You should see:
```
🚀 GameForge API server running on port 3001
📝 Environment: development
🌐 CORS enabled for: http://localhost:5000
💾 Database: Connected
```

### B. Start Your Frontend Server

```bash
# In a new terminal
npm run dev
```

You should see:
```
VITE v6.3.5  ready in 452 ms
➜  Local:   http://localhost:5000/
```

### C. Test GitHub OAuth

1. Go to: http://localhost:5000/login
2. Click "Continue with GitHub"
3. You should be redirected to GitHub
4. Authorize your app
5. You should be redirected back and logged in

### D. Test Google OAuth

1. Go to: http://localhost:5000/login
2. Click "Continue with Google"
3. You should see Google's sign-in page
4. Sign in with your Google account
5. You should be redirected back and logged in

---

## 🔧 **Verification Commands**

Run this to check your configuration:
```bash
node check-oauth-config.js
```

You should see all green checkmarks ✅ when properly configured.

---

## 🚨 **Common Issues & Solutions**

### GitHub Issues

**❌ "The redirect_uri MUST match the registered callback URL"**
- Solution: Double-check your callback URL is exactly: `http://localhost:3001/api/auth/github/callback`

**❌ "Bad credentials"**
- Solution: Verify your Client ID and Client Secret in the `.env` file

### Google Issues

**❌ "Error 400: redirect_uri_mismatch"**
- Solution: Ensure redirect URI is exactly: `http://localhost:3001/api/auth/google/callback`

**❌ "This app isn't verified"**
- Solution: Click "Advanced" → "Go to GameForge (unsafe)" (this is normal in development)

**❌ "access_blocked"**
- Solution: Make sure you added your email as a test user in the OAuth consent screen

---

## 📱 **What You'll See When Working**

### Login Page Features:
- Beautiful GitHub button (dark theme with GitHub logo)
- Elegant Google button (Google brand colors with G logo)
- Clean separation between OAuth and email/password options
- Responsive design that works on all devices

### OAuth Flow:
1. User clicks OAuth button
2. Redirected to provider (GitHub/Google)
3. User authorizes your app
4. Redirected back to your app
5. User automatically logged in
6. Redirected to dashboard

---

## 🎯 **Success Checklist**

- [ ] GitHub OAuth app created with correct callback URL
- [ ] GitHub credentials added to `.env` file
- [ ] Google Cloud project created
- [ ] Google OAuth consent screen configured
- [ ] Google OAuth credentials created with correct redirect URI
- [ ] Google credentials added to `.env` file
- [ ] Backend server restarted and running
- [ ] Frontend server running
- [ ] Tested GitHub OAuth flow successfully
- [ ] Tested Google OAuth flow successfully

---

## 🎉 **Once Complete**

Your GameForge application will have:
- ✅ **Secure OAuth authentication** with GitHub and Google
- ✅ **Professional login experience** with branded OAuth buttons
- ✅ **Seamless user registration** - no email/password required
- ✅ **Automatic user profile creation** with OAuth provider data
- ✅ **JWT token-based authentication** for API access

**Next Steps After OAuth Setup:**
1. Customize OAuth button styling (optional)
2. Add additional OAuth providers like Discord, Twitter (optional)
3. Set up production OAuth applications for deployment
4. Configure proper error handling for production use

You're building something amazing! 🚀
