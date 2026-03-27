#!/usr/bin/env python3
"""
Simplified API tests without pandas dependency
Testes simplificados de APIs sem dependência do pandas
"""

import requests
import json

def test_bcb_ipca():
    """Testa dados do BCB para IPCA (proxy para Tesouro IPCA+)"""

    print("Testing BCB IPCA data...")

    end_date = "27/03/2026"
    start_date = "01/01/2026"

    try:
        # IPCA - série 433
        ipca_url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial={start_date}&dataFinal={end_date}"

        response = requests.get(ipca_url, timeout=10)
        response.raise_for_status()

        data = response.json()

        print("✅ BCB IPCA API - Success")
        print(f"Records found: {len(data)}")

        if data:
            print("Sample IPCA data:")
            print(json.dumps(data[-3:], indent=2))

        return True, data

    except Exception as e:
        print(f"❌ BCB IPCA API - Error: {e}")
        return False, None

def test_cvm_simple():
    """Testa acesso simples aos dados da CVM"""

    print("Testing CVM website access...")

    try:
        # Test if CVM data portal is accessible
        url = "http://dados.cvm.gov.br"

        response = requests.get(url, timeout=10)

        print(f"CVM Data Portal Status: {response.status_code}")

        if response.status_code == 200:
            print("✅ CVM data portal accessible")

            # Check if fund data URL is accessible
            fund_url = "http://dados.cvm.gov.br/dados/FI/CAD/DADOS/"
            fund_response = requests.get(fund_url, timeout=10)

            print(f"CVM Fund Data Directory: {fund_response.status_code}")

            return True, response.status_code
        else:
            print("❌ CVM data portal not accessible")
            return False, None

    except Exception as e:
        print(f"❌ CVM - Error: {e}")
        return False, None

def test_yahoo_finance_simple():
    """Teste simples do Yahoo Finance para ETF de Tesouro"""

    print("Testing Yahoo Finance for Treasury ETF...")

    try:
        # TREA11 = Tesouro IPCA+ ETF na B3
        url = "https://query1.finance.yahoo.com/v8/finance/chart/TREA11.SA"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get('chart', {}).get('result'):
            print("✅ Yahoo Finance - Treasury ETF data available")

            result = data['chart']['result'][0]
            meta = result['meta']

            print(f"Symbol: {meta['symbol']}")
            print(f"Current Price: {meta.get('regularMarketPrice', 'N/A')}")
            print(f"Currency: {meta.get('currency', 'N/A')}")

            return True, data
        else:
            print("❌ Yahoo Finance - No Treasury ETF data")
            return False, None

    except Exception as e:
        print(f"❌ Yahoo Finance - Error: {e}")
        return False, None

def test_newsapi_structure():
    """Testa estrutura da News API (sem chave)"""

    print("Testing NewsAPI structure...")

    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': 'Nubank',
            'language': 'pt',
            'sortBy': 'publishedAt',
            'pageSize': 5
        }

        response = requests.get(url, params=params, timeout=10)

        print(f"NewsAPI Status: {response.status_code}")

        if response.status_code == 401:
            print("✅ NewsAPI endpoint working (API key required)")
            try:
                error_data = response.json()
                print(f"Error message: {error_data.get('message', 'N/A')}")
            except:
                pass
            return True, 401
        elif response.status_code == 200:
            data = response.json()
            print("✅ NewsAPI working without API key")
            print(json.dumps(data, indent=2))
            return True, data
        else:
            print(f"❌ NewsAPI unexpected status: {response.status_code}")
            return False, None

    except Exception as e:
        print(f"❌ NewsAPI - Error: {e}")
        return False, None

def test_alternative_treasury():
    """Testa fontes alternativas para dados do Tesouro"""

    print("Testing alternative Treasury data sources...")

    # 1. Test Tesouro Nacional website
    try:
        url = "https://www.tesouronacional.gov.br"
        response = requests.get(url, timeout=10)

        print(f"Tesouro Nacional website: {response.status_code}")

        if response.status_code == 200:
            print("✅ Tesouro Nacional website accessible")

            # Check for any API mentions
            content = response.text.lower()
            api_keywords = ['api', 'dados', 'json', 'csv']
            found = [kw for kw in api_keywords if kw in content]

            print(f"Data-related keywords found: {found}")

            return True, response.status_code
        else:
            print("❌ Tesouro Nacional website not accessible")
            return False, None

    except Exception as e:
        print(f"❌ Tesouro Nacional - Error: {e}")
        return False, None

def main():
    """Execute simplified API tests"""

    print("=" * 60)
    print("TESTES SIMPLIFICADOS DE APIs")
    print("=" * 60)

    results = {}

    # Test BCB IPCA as proxy for Treasury IPCA+
    print("\n1. Testing BCB IPCA...")
    results['bcb_ipca'] = test_bcb_ipca()

    # Test CVM access
    print("\n2. Testing CVM access...")
    results['cvm_access'] = test_cvm_simple()

    # Test Yahoo Finance for Treasury ETF
    print("\n3. Testing Yahoo Finance Treasury ETF...")
    results['yahoo_treasury'] = test_yahoo_finance_simple()

    # Test NewsAPI structure
    print("\n4. Testing NewsAPI structure...")
    results['newsapi'] = test_newsapi_structure()

    # Test alternative Treasury sources
    print("\n5. Testing alternative Treasury sources...")
    results['treasury_alt'] = test_alternative_treasury()

    # Summary
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES SIMPLIFICADOS")
    print("=" * 60)

    for api, (success, data) in results.items():
        status = "✅ FUNCIONANDO" if success else "❌ FALHOU"
        print(f"{api:20} {status}")

    # Final Recommendations
    print("\n" + "=" * 60)
    print("RECOMENDAÇÕES TÉCNICAS FINAIS")
    print("=" * 60)

    working_apis = sum(1 for success, _ in results.values() if success)

    print("DADOS PRIMÁRIOS (APIs oficiais):")
    if results['bcb_ipca'][0]:
        print("✅ BCB IPCA como proxy para Tesouro IPCA+")

    print("\nDADOS ALTERNATIVOS:")
    if results['yahoo_treasury'][0]:
        print("✅ Yahoo Finance para ETF de Tesouro (TREA11)")

    if results['cvm_access'][0]:
        print("✅ CVM portal acessível para dados de fundos")

    if results['newsapi'][0]:
        print("✅ NewsAPI disponível (requer API key)")

    print(f"\nTotal de fontes funcionais: {working_apis}/5")

    if working_apis >= 3:
        print("\n✅ SUFICIENTES APIs para implementação do sistema")
    else:
        print("\n⚠️  POUCAS APIs - necessário mais fallbacks")

    return results

if __name__ == "__main__":
    results = main()