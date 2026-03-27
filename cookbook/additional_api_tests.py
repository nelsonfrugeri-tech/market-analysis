#!/usr/bin/env python3
"""
Additional API tests for Treasury and CVM data
Testes adicionais para dados do Tesouro e CVM
"""

import requests
import pandas as pd
from io import StringIO
import json

def test_cvm_fundos():
    """Testa dados da CVM para fundos de investimento"""

    print("Testing CVM Fund Data...")

    # URL atualizada da CVM para dados de fundos
    url = "http://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        print("✅ CVM Fundos Data - Success")
        print(f"Status Code: {response.status_code}")
        print(f"Content size: {len(response.content)} bytes")

        # Read CSV and search for Nubank funds
        df = pd.read_csv(StringIO(response.text), sep=';', encoding='latin-1')

        print(f"Total de fundos: {len(df)}")
        print(f"Colunas disponíveis: {list(df.columns)}")

        # Search for Nubank funds
        if 'DENOM_SOCIAL' in df.columns:
            nubank_funds = df[df['DENOM_SOCIAL'].str.contains('NUBANK|Nu Asset|Nu Pagamentos', case=False, na=False)]
            print(f"\nFundos do Nubank encontrados: {len(nubank_funds)}")

            if len(nubank_funds) > 0:
                print("\nFundos do Nubank:")
                for idx, row in nubank_funds.iterrows():
                    print(f"- CNPJ: {row['CNPJ_FUNDO']} | Nome: {row['DENOM_SOCIAL']}")

        return True, df

    except Exception as e:
        print(f"❌ CVM Fundos Data - Error: {e}")
        return False, None

def test_alternative_treasury_apis():
    """Testa APIs alternativas para dados do Tesouro"""

    print("\nTesting Alternative Treasury APIs...")

    # 1. Try different Tesouro Nacional endpoint
    try:
        url = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_search"
        params = {
            'q': 'tesouro direto',
            'rows': 5
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get('success'):
            print("✅ Tesouro Transparente - Package search working")
            print(f"Packages found: {len(data['result']['results'])}")

            # List available datasets
            for pkg in data['result']['results'][:3]:
                print(f"- Dataset: {pkg['title']}")
                if pkg.get('resources'):
                    print(f"  Resources: {len(pkg['resources'])}")

            return True, data
        else:
            print("❌ Tesouro Transparente - No success flag")
            return False, None

    except Exception as e:
        print(f"❌ Tesouro Transparente - Error: {e}")
        return False, None

def test_bcb_tesouro_selic():
    """Testa dados do BCB relacionados ao Tesouro SELIC"""

    print("\nTesting BCB Treasury SELIC data...")

    # Taxa básica de juros (Meta SELIC) - série 432
    # IPCA - série 433
    end_date = "27/03/2026"
    start_date = "01/03/2026"

    try:
        # Test IPCA data from BCB
        ipca_url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial={start_date}&dataFinal={end_date}"

        response = requests.get(ipca_url, timeout=10)
        response.raise_for_status()

        data = response.json()

        print("✅ BCB IPCA API - Success")
        print(f"Records found: {len(data)}")

        if data:
            print("Sample IPCA data:")
            print(json.dumps(data[-2:], indent=2))

        return True, data

    except Exception as e:
        print(f"❌ BCB IPCA API - Error: {e}")
        return False, None

def test_yahoo_finance_br():
    """Testa Yahoo Finance para dados brasileiros"""

    print("\nTesting Yahoo Finance for Brazilian data...")

    try:
        # Test Brazilian Treasury bond ETF or similar
        # TREA11 = Tesouro IPCA+ ETF
        url = "https://query1.finance.yahoo.com/v8/finance/chart/TREA11.SA"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get('chart', {}).get('result'):
            print("✅ Yahoo Finance BR - Success")
            print("Found Treasury ETF data (TREA11)")

            result = data['chart']['result'][0]
            meta = result['meta']

            print(f"Symbol: {meta['symbol']}")
            print(f"Regular Market Price: {meta.get('regularMarketPrice', 'N/A')}")
            print(f"Currency: {meta.get('currency', 'N/A')}")

            return True, data
        else:
            print("❌ Yahoo Finance BR - No data found")
            return False, None

    except Exception as e:
        print(f"❌ Yahoo Finance BR - Error: {e}")
        return False, None

def test_b3_api():
    """Testa se B3 tem alguma API pública"""

    print("\nTesting B3 (Brazilian Stock Exchange) access...")

    try:
        # B3 public market data endpoint
        url = "https://www.b3.com.br/pt_br/market-data-e-indices/"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)

        print(f"B3 Website Status: {response.status_code}")

        if response.status_code == 200:
            print("✅ B3 website accessible")

            # Check if there are any API references
            content = response.text.lower()
            api_indicators = ['api', 'json', 'rest', 'endpoint']
            found = [indicator for indicator in api_indicators if indicator in content]

            print(f"API indicators found in content: {found}")

            return True, response.status_code
        else:
            print("❌ B3 website not accessible")
            return False, None

    except Exception as e:
        print(f"❌ B3 - Error: {e}")
        return False, None

def main():
    """Execute all additional API tests"""

    print("=" * 60)
    print("TESTES ADICIONAIS - TREASURY E CVM")
    print("=" * 60)

    results = {}

    # Test CVM fund data
    print("\n1. Testing CVM Fund Data...")
    results['cvm_fundos'] = test_cvm_fundos()

    # Test alternative Treasury APIs
    print("\n2. Testing Alternative Treasury APIs...")
    results['treasury_alt'] = test_alternative_treasury_apis()

    # Test BCB for Treasury-related data
    print("\n3. Testing BCB Treasury/IPCA data...")
    results['bcb_ipca'] = test_bcb_tesouro_selic()

    # Test Yahoo Finance Brazil
    print("\n4. Testing Yahoo Finance Brazil...")
    results['yahoo_br'] = test_yahoo_finance_br()

    # Test B3
    print("\n5. Testing B3 access...")
    results['b3'] = test_b3_api()

    # Summary
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES ADICIONAIS")
    print("=" * 60)

    for api, (success, data) in results.items():
        status = "✅ FUNCIONANDO" if success else "❌ FALHOU"
        print(f"{api:20} {status}")

    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMENDAÇÕES FINAIS")
    print("=" * 60)

    working_apis = sum(1 for success, _ in results.values() if success)

    if results['cvm_fundos'][0]:
        print("✅ CVM dados disponíveis - usar para fundos do Nubank")

    if results['bcb_ipca'][0]:
        print("✅ BCB IPCA disponível - usar como proxy para Tesouro IPCA+")

    if results['yahoo_br'][0]:
        print("✅ Yahoo Finance BR disponível - usar para ETFs de Tesouro")

    print(f"\nAPIs adicionais funcionando: {working_apis}/5")

    return results

if __name__ == "__main__":
    results = main()