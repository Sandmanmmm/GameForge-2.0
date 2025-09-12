#!/usr/bin/env node

// Quick test script to verify SDXL integration
const fetch = require('node-fetch');

const API_BASE = 'http://localhost:3001/api';
const SDXL_BASE = 'http://localhost:8000';

async function testSDXLIntegration() {
  console.log('🧪 Testing SDXL Integration...\n');
  
  try {
    // 1. Check SDXL service health
    console.log('1️⃣ Checking SDXL service health...');
    const healthResponse = await fetch(`${SDXL_BASE}/health`);
    const health = await healthResponse.json();
    console.log(`   Status: ${health.status}`);
    console.log(`   Generation method: ${health.generation_method}`);
    console.log(`   Model status: ${health.model_status}`);
    
    if (health.model_status !== 'loaded') {
      console.log('   ⚠️  SDXL model not loaded. Loading now...');
      const loadResponse = await fetch(`${SDXL_BASE}/load-model`, { method: 'POST' });
      const loadResult = await loadResponse.json();
      console.log(`   Load result: ${loadResult.message}`);
    }
    
    // 2. Test asset generation via GameForge API
    console.log('\n2️⃣ Testing asset generation via GameForge API...');
    const generateResponse = await fetch(`${API_BASE}/ai/assets`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt: 'medieval fantasy sword sprite, detailed pixel art style, glowing blue blade',
        assetType: 'sprite',
        style: 'pixel art',
        size: 'medium',
        count: 1,
        provider: 'local'
      })
    });
    
    const generateResult = await generateResponse.json();
    
    if (generateResult.success && generateResult.data.jobId) {
      const jobId = generateResult.data.jobId;
      console.log(`   ✅ Generation job started: ${jobId}`);
      console.log(`   Tracking URL: ${generateResult.data.trackingUrl}`);
      
      // 3. Poll for results
      console.log('\n3️⃣ Polling for results...');
      let attempts = 0;
      const maxAttempts = 20; // 2 minutes max
      
      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 6000)); // Wait 6 seconds
        
        const statusResponse = await fetch(`${API_BASE}/ai/jobs/${jobId}`);
        const status = await statusResponse.json();
        
        attempts++;
        console.log(`   Poll ${attempts}: ${status.data?.status || 'unknown'} - ${status.data?.message || 'No message'}`);
        
        if (status.success && status.data?.status === 'completed') {
          console.log('\n✅ SDXL Integration Test PASSED!');
          console.log(`   Generated ${status.data.assets?.length || 0} assets`);
          
          if (status.data.assets && status.data.assets.length > 0) {
            const asset = status.data.assets[0];
            console.log(`   Asset URL: ${asset.url}`);
            console.log(`   Generation method: ${asset.metadata?.generationMethod}`);
            console.log(`   SDXL model: ${asset.metadata?.sdxlModel}`);
            console.log(`   Processing time: ${asset.metadata?.processingTime}s`);
          }
          return;
        } else if (status.data?.status === 'failed') {
          console.log('\n❌ SDXL Integration Test FAILED!');
          console.log(`   Error: ${status.data.message}`);
          return;
        }
      }
      
      console.log('\n⏰ Test timed out after 2 minutes');
    } else {
      console.log('   ❌ Failed to start generation job');
      console.log(`   Error: ${generateResult.error?.message || 'Unknown error'}`);
    }
    
  } catch (error) {
    console.log('\n💥 Integration test failed with error:');
    console.error(error.message);
  }
}

// Run the test
testSDXLIntegration();
