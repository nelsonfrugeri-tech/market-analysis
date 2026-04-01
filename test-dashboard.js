// Simple test script to validate dashboard functionality
const { execSync } = require('child_process');

console.log('🔍 Testing dashboard functionality...\n');

// Test 1: Backend API
try {
  const fundsResponse = execSync('curl -s http://localhost:8000/api/v1/funds', { encoding: 'utf8' });
  const funds = JSON.parse(fundsResponse);
  console.log('✅ Backend API: Working');
  console.log(`   Found ${funds.length} fund(s): ${funds[0]?.name}`);
} catch (error) {
  console.log('❌ Backend API: Failed');
  console.log(`   Error: ${error.message}`);
}

// Test 2: Frontend proxy
try {
  const proxyResponse = execSync('curl -s http://localhost:3001/api/v1/funds', { encoding: 'utf8' });
  const proxyFunds = JSON.parse(proxyResponse);
  console.log('✅ Frontend proxy: Working');
  console.log(`   Proxy returns ${proxyFunds.length} fund(s)`);
} catch (error) {
  console.log('❌ Frontend proxy: Failed');
  console.log(`   Error: ${error.message}`);
}

// Test 3: Frontend HTML
try {
  const htmlResponse = execSync('curl -s http://localhost:3001', { encoding: 'utf8' });
  const hasTitle = htmlResponse.includes('Market Analysis Dashboard');
  const hasLoading = htmlResponse.includes('Loading funds');
  console.log(`✅ Frontend HTML: ${hasTitle ? 'Working' : 'Failed'}`);
  console.log(`   Title found: ${hasTitle}`);
  console.log(`   Loading state: ${hasLoading}`);
} catch (error) {
  console.log('❌ Frontend HTML: Failed');
  console.log(`   Error: ${error.message}`);
}

console.log('\n🎯 Dashboard test completed!');