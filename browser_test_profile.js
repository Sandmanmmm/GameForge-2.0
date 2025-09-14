// Test the profile update in browser console
// 1. Open browser developer tools (F12)
// 2. Go to the GameForge app at http://localhost:5002
// 3. Login first if not already logged in
// 4. Run this in the console:

async function testProfileUpdate() {
    console.log('🧪 Testing Profile Update');
    
    // Get current auth token
    const token = localStorage.getItem('token');
    if (!token) {
        console.error('❌ No auth token found. Please login first.');
        return;
    }
    
    console.log('✅ Found auth token');
    
    // Get current user
    const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
    console.log('Current user:', currentUser);
    console.log('Current name:', currentUser.name);
    
    // Test API call
    const newName = `Test Name ${new Date().getTime()}`;
    console.log(`🔄 Updating name to: ${newName}`);
    
    try {
        const response = await fetch('http://localhost:8080/api/v1/auth/me', {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: newName })
        });
        
        console.log('Response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Update successful!');
            console.log('Response data:', data);
            console.log('New name in response:', data.user?.name);
            
            // Check if localStorage was updated (should happen automatically by AuthContext)
            setTimeout(() => {
                const updatedUser = JSON.parse(localStorage.getItem('user') || '{}');
                console.log('Updated user in localStorage:', updatedUser);
                console.log('Updated name in localStorage:', updatedUser.name);
                
                if (updatedUser.name === newName) {
                    console.log('🎉 SUCCESS: Name persisted correctly!');
                } else {
                    console.log('❌ FAILURE: Name not persisted in localStorage');
                }
            }, 100);
            
        } else {
            const errorData = await response.text();
            console.error('❌ Update failed:', response.status, errorData);
        }
        
    } catch (error) {
        console.error('❌ Network error:', error);
    }
}

// Run the test
testProfileUpdate();