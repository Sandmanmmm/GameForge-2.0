// Complete Profile Update Test Script
// Run this in browser console while on the GameForge app

console.log('=== Starting Complete Profile Update Test ===');

// 1. Check current authentication state
console.log('Current auth state:');
console.log('- localStorage user:', JSON.parse(localStorage.getItem('user') || 'null'));
console.log('- localStorage token:', localStorage.getItem('token'));

// 2. Test the API directly
async function testProfileUpdate() {
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      console.error('No authentication token found!');
      return;
    }

    console.log('\n=== Testing Direct API Call ===');
    
    // First, get current profile
    const getCurrentProfile = await fetch('http://localhost:8001/api/v1/auth/me', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (getCurrentProfile.ok) {
      const currentData = await getCurrentProfile.json();
      console.log('Current profile from API:', currentData);
    } else {
      console.error('Failed to get current profile:', getCurrentProfile.status);
      return;
    }

    // Now test updating the profile
    const testName = `TestUser_${Date.now()}`;
    console.log(`Attempting to update profile with name: ${testName}`);
    
    const response = await fetch('http://localhost:8001/api/v1/auth/me', {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: testName
      })
    });

    if (response.ok) {
      const data = await response.json();
      console.log('✅ Profile update successful!');
      console.log('Response data:', data);
      
      // Verify the update persisted by fetching again
      const verifyResponse = await fetch('http://localhost:8001/api/v1/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (verifyResponse.ok) {
        const verifyData = await verifyResponse.json();
        console.log('✅ Verification fetch successful!');
        console.log('Verified profile data:', verifyData);
        
        if (verifyData.name === testName) {
          console.log('✅ DATABASE PERSISTENCE CONFIRMED: Name was saved and retrieved!');
        } else {
          console.log('❌ DATABASE PERSISTENCE FAILED: Name was not saved properly');
          console.log(`Expected: ${testName}, Got: ${verifyData.name}`);
        }
      } else {
        console.error('❌ Failed to verify profile update:', verifyResponse.status);
      }
      
    } else {
      console.error('❌ Profile update failed:', response.status);
      const errorData = await response.text();
      console.error('Error details:', errorData);
    }
  } catch (error) {
    console.error('❌ Test failed with error:', error);
  }
}

// 3. Test frontend state management
function testFrontendState() {
  console.log('\n=== Testing Frontend State ===');
  
  // Check if we're on the profile page
  const profileElements = document.querySelectorAll('[data-testid="profile"], .profile, h3');
  console.log('Profile-related elements found:', profileElements.length);
  
  profileElements.forEach((el, index) => {
    console.log(`Element ${index}:`, el.textContent, el.className);
  });
  
  // Look for user name displays
  const userNameElements = document.querySelectorAll('*');
  const nameMatches = [];
  userNameElements.forEach(el => {
    if (el.textContent && (el.textContent.includes('User') || el.textContent.includes('TestUser'))) {
      nameMatches.push({
        element: el.tagName,
        text: el.textContent.trim(),
        className: el.className
      });
    }
  });
  
  console.log('Elements containing "User" or "TestUser":', nameMatches);
}

// 4. Run complete test
async function runCompleteTest() {
  await testProfileUpdate();
  testFrontendState();
  
  console.log('\n=== Test Complete ===');
  console.log('Check the above results for any issues.');
  console.log('If database persistence is working but frontend isn\'t updating,');
  console.log('the issue is in the AuthContext state management.');
}

// Run the test
runCompleteTest();