// Test script to verify API endpoints are working correctly

async function testEndpoints() {
  console.log('🔍 Testing API endpoints...\n')

  try {
    // Test funds endpoint
    console.log('1. Testing funds endpoint...')
    const fundsResponse = await fetch('http://localhost:3001/api/v1/funds')
    const funds = await fundsResponse.json()
    console.log('✅ Funds:', funds.length, 'funds found')

    if (funds.length > 0) {
      const testFund = funds[0]
      console.log('📁 Test fund:', testFund.name, '(' + testFund.cnpj + ')')

      // Test performance endpoint
      console.log('\n2. Testing performance endpoint...')
      const encoded = encodeURIComponent(testFund.cnpj)
      const perfUrl = `http://localhost:3001/api/v1/funds/${encoded}/performance?months=6`
      console.log('📡 URL:', perfUrl)

      const perfResponse = await fetch(perfUrl)
      console.log('📊 Response status:', perfResponse.status)

      if (perfResponse.ok) {
        const perfData = await perfResponse.json()
        console.log('✅ Performance data received')
        console.log('💰 Total return:', perfData.performance.return_pct + '%')
        console.log('⚠️ Volatility:', perfData.risk.volatility)
        console.log('📈 Sharpe ratio:', perfData.risk.sharpe_ratio)
      } else {
        const errorText = await perfResponse.text()
        console.log('❌ Performance endpoint failed:', errorText)
      }
    }

    console.log('\n✅ API test completed!')

  } catch (error) {
    console.error('❌ Error testing endpoints:', error.message)
  }
}

testEndpoints()