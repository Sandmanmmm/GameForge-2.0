// OAuth Test Script for GameForge
// This script tests the OAuth endpoints and provides setup instructions

console.log('🔐 GameForge OAuth Integration Test\n');

// Test backend endpoints
const BASE_URL = 'http://localhost:3001';
const endpoints = [
  '/api/health',
  '/api/auth/github',
  '/api/auth/google'
];

async function testEndpoint(endpoint) {
  try {
    const response = await fetch(`${BASE_URL}${endpoint}`, { method: 'GET' });
    return {
      endpoint,
      status: response.status,
      ok: response.ok,
      headers: Object.fromEntries(response.headers.entries())
    };
  } catch (error) {
    return {
      endpoint,
      error: error.message
    };
  }
}

async function runTests() {
  console.log('Testing backend endpoints...\n');
  
  for (const endpoint of endpoints) {
    const result = await testEndpoint(endpoint);
    console.log(`📍 ${endpoint}:`);
    
    if (result.error) {
      console.log(`   ❌ Error: ${result.error}`);
    } else {
      console.log(`   ✅ Status: ${result.status} (${result.ok ? 'OK' : 'Error'})`);
      if (endpoint.includes('auth/')) {
        console.log(`   🔄 Should redirect to OAuth provider`);
      }
    }
    console.log('');
  }
  
  console.log('🎯 OAuth Setup Instructions:');
  console.log('1. GitHub OAuth:');
  console.log('   - Go to https://github.com/settings/developers');
  console.log('   - Create new OAuth App');
  console.log('   - Authorization callback URL: http://localhost:3001/api/auth/github/callback');
  console.log('   - Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in backend/.env');
  console.log('');
  console.log('2. Google OAuth:');
  console.log('   - Go to https://console.cloud.google.com/apis/credentials');
  console.log('   - Create OAuth 2.0 Client ID');
  console.log('   - Authorized redirect URI: http://localhost:3001/api/auth/google/callback');
  console.log('   - Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env');
  console.log('');
  console.log('3. Frontend URLs:');
  console.log('   - Login: http://localhost:5000/login');
  console.log('   - Register: http://localhost:5000/register');
  console.log('   - OAuth Callback: http://localhost:5000/auth/callback');
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { testEndpoint, runTests };
} else {
  runTests();
}
