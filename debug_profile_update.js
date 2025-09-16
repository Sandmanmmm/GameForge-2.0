// Debug Profile Update - Run this in browser console
console.log('🔍 Debugging Profile Update');

// 1. Check current auth state
const token = localStorage.getItem('token');
const user = JSON.parse(localStorage.getItem('user') || '{}');
console.log('Current token:', token ? 'Present' : 'Missing');
console.log('Current user:', user);

// 2. Test the API endpoint directly
async function testProfileUpdate() {
    console.log('🧪 Testing Profile Update API');
    
    if (!token) {
        console.error('❌ No auth token found');
        return;
    }
    
    const testName = `Test Name ${Date.now()}`;
    console.log(`🔄 Updating name to: ${testName}`);
    
    try {
        const response = await fetch('http://localhost:8080/api/v1/auth/me', {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: testName })
        });
        
        console.log('Response status:', response.status);
        console.log('Response headers:', Object.fromEntries(response.headers.entries()));
        
        const responseData = await response.text();
        console.log('Response body:', responseData);
        
        if (response.ok) {
            try {
                const data = JSON.parse(responseData);
                console.log('✅ Update successful!');
                console.log('New user data:', data.user);
                console.log('New token provided:', !!data.access_token);
            } catch (e) {
                console.log('Response was OK but not JSON:', responseData);
            }
        } else {
            console.error('❌ Update failed:', response.status, responseData);
        }
        
    } catch (error) {
        console.error('❌ Network error:', error);
    }
}

// 3. Check AuthContext state
console.log('AuthContext user from React:', window.React?.version ? 'Available' : 'Not available');

// Run the test
testProfileUpdate();