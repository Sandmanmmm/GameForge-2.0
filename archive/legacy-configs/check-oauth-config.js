#!/usr/bin/env node

/**
 * OAuth Configuration Checker
 * Verifies that OAuth environment variables are properly configured
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('🔐 GameForge OAuth Configuration Checker\n');

// Check if .env file exists
const envPath = path.join(__dirname, 'backend', '.env');

if (!fs.existsSync(envPath)) {
    console.log('❌ Error: backend/.env file not found!');
    console.log('   Please create a .env file in the backend directory.');
    process.exit(1);
}

// Read .env file
const envContent = fs.readFileSync(envPath, 'utf8');
const envVars = {};

// Parse .env file
envContent.split('\n').forEach(line => {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#')) {
        const [key, ...valueParts] = trimmed.split('=');
        if (key && valueParts.length > 0) {
            envVars[key] = valueParts.join('=').replace(/^["']|["']$/g, '');
        }
    }
});

console.log('📋 Environment Variables Check:\n');

// Check required OAuth variables
const oauthVars = {
    'GITHUB_CLIENT_ID': 'GitHub Client ID',
    'GITHUB_CLIENT_SECRET': 'GitHub Client Secret',
    'GOOGLE_CLIENT_ID': 'Google Client ID',
    'GOOGLE_CLIENT_SECRET': 'Google Client Secret'
};

let allConfigured = true;
let hasPlaceholders = false;

Object.entries(oauthVars).forEach(([envVar, description]) => {
    const value = envVars[envVar];
    
    if (!value) {
        console.log(`❌ ${envVar}: Missing`);
        allConfigured = false;
    } else if (value.includes('your_') || value.includes('_here')) {
        console.log(`⚠️  ${envVar}: Contains placeholder value`);
        console.log(`   Current: ${value}`);
        hasPlaceholders = true;
        allConfigured = false;
    } else {
        console.log(`✅ ${envVar}: Configured`);
        console.log(`   Value: ${value.substring(0, 20)}...`);
    }
    console.log('');
});

// Check other important variables
console.log('📋 Other Configuration:\n');

const otherVars = {
    'JWT_SECRET': 'JWT Secret Key',
    'SESSION_SECRET': 'Session Secret Key',
    'FRONTEND_URL': 'Frontend URL',
    'DATABASE_URL': 'Database Connection'
};

Object.entries(otherVars).forEach(([envVar, description]) => {
    const value = envVars[envVar];
    
    if (!value) {
        console.log(`❌ ${envVar}: Missing`);
    } else if (value.includes('your-') || value.includes('change-this')) {
        console.log(`⚠️  ${envVar}: Using default/placeholder value`);
        if (envVar.includes('SECRET')) {
            console.log(`   Consider updating for security`);
        }
    } else {
        console.log(`✅ ${envVar}: Configured`);
    }
    console.log('');
});

// Summary
console.log('🎯 Summary:\n');

if (allConfigured && !hasPlaceholders) {
    console.log('🎉 All OAuth variables are properly configured!');
    console.log('   You can now test your OAuth integration.');
} else {
    console.log('⚠️  OAuth configuration incomplete:');
    
    if (hasPlaceholders) {
        console.log('   • Replace placeholder values with actual OAuth credentials');
    }
    
    console.log('   • Follow the setup guide in oauth-provider-setup.md');
    console.log('   • Restart your backend server after making changes');
}

console.log('\n📚 Next Steps:');
console.log('1. Set up GitHub OAuth app: https://github.com/settings/developers');
console.log('2. Set up Google OAuth app: https://console.cloud.google.com/');
console.log('3. Update your backend/.env file with real credentials');
console.log('4. Restart backend server: cd backend && npm run dev');
console.log('5. Test OAuth: Go to http://localhost:5000/login');

// Show current callback URLs that should be configured
console.log('\n🔗 OAuth Callback URLs to Configure:');
console.log('GitHub: http://localhost:3001/api/auth/github/callback');
console.log('Google: http://localhost:3001/api/auth/google/callback');
