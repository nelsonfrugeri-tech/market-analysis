#!/usr/bin/env python3
"""
API Investigation Script for Market Analysis System
Testa APIs disponíveis para coleta de dados financeiros
"""

import requests
import json
from datetime import datetime, timedelta
import time

def test_bcb_selic():
    """Testa API do BCB para taxa SELIC"""

    end_date = datetime.now().strftime('%d/%m/%Y')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%d/%m/%Y')

    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial={start_date}&dataFinal={end_date}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        print("✅ BCB SELIC API - Success")
        print(f"Status Code: {response.status_code}")
        print(f"Records found: {len(data)}")

        if data:
            print("Sample data:")
            print(json.dumps(data[-2:], indent=2))

        return True, data

    except Exception as e:
        print(f"❌ BCB SELIC API - Error: {e}")
        return False, None

def test_bcb_cdi():
    """Testa API do BCB para taxa CDI"""

    end_date = datetime.now().strftime('%d/%m/%Y')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%d/%m/%Y')

    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.4389/dados?formato=json&dataInicial={start_date}&dataFinal={end_date}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        print("✅ BCB CDI API - Success")
        print(f"Status Code: {response.status_code}")
        print(f"Records found: {len(data)}")

        if data:
            print("Sample data:")
            print(json.dumps(data[-2:], indent=2))

        return True, data

    except Exception as e:
        print(f"❌ BCB CDI API - Error: {e}")
        return False, None

def test_tesouro_direto():
    """Testa API do Tesouro Direto"""

    url = "https://www.tesourotransparente.gov.br/ckan/api/3/action/datastore_search"

    params = {
        'resource_id': 'af63adf4-68a0-4f36-9aa5-0c8c89d4e8ff',
        'limit': 10
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        print("✅ Tesouro Direto API - Success")
        print(f"Status Code: {response.status_code}")

        if data.get('success'):
            records = data['result']['records']
            print(f"Records found: {len(records)}")

            if records:
                print("Sample data:")
                print(json.dumps(records[:2], indent=2))

        return True, data

    except Exception as e:
        print(f"❌ Tesouro Direto API - Error: {e}")
        return False, None

def test_google_news_rss():
    """Testa RSS feed do Google News para notícias do Nubank"""

    import xml.etree.ElementTree as ET

    url = "https://news.google.com/rss/search?q=Nubank&hl=pt-BR&gl=BR&ceid=BR:pt-419"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        print("✅ Google News RSS - Success")
        print(f"Status Code: {response.status_code}")

        # Parse XML
        root = ET.fromstring(response.content)

        items = root.findall('.//item')
        print(f"Articles found: {len(items)}")

        if items:
            print("\nSample articles:")
            for i, item in enumerate(items[:3]):
                title = item.find('title').text if item.find('title') is not None else 'N/A'
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else 'N/A'
                print(f"{i+1}. {title} ({pub_date})")

        return True, items

    except Exception as e:
        print(f"❌ Google News RSS - Error: {e}")
        return False, None

def test_maisretorno():
    """Testa acesso ao MaisRetorno"""

    url = "https://maisretorno.com"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        print("📊 MaisRetorno - Accessibility test")
        print(f"Status Code: {response.status_code}")
        print(f"Content size: {len(response.content)} bytes")

        if response.status_code == 200:
            print("✅ Website accessible, would require scraping")
            return True, response.status_code

        return False, response.status_code

    except Exception as e:
        print(f"❌ MaisRetorno - Error: {e}")
        return False, None

def main():
    """Executa todos os testes de API"""

    print("=" * 60)
    print("TESTE DE APIs - MARKET ANALYSIS SYSTEM")
    print("=" * 60)

    results = {}

    # Test BCB APIs
    print("\n1. Testing BCB SELIC...")
    results['bcb_selic'] = test_bcb_selic()

    print("\n2. Testing BCB CDI...")
    results['bcb_cdi'] = test_bcb_cdi()

    # Test Tesouro Direto
    print("\n3. Testing Tesouro Direto...")
    results['tesouro'] = test_tesouro_direto()

    # Test News
    print("\n4. Testing Google News RSS...")
    results['news'] = test_google_news_rss()

    # Test MaisRetorno
    print("\n5. Testing MaisRetorno...")
    results['maisretorno'] = test_maisretorno()

    # Summary
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)

    for api, (success, data) in results.items():
        status = "✅ FUNCIONANDO" if success else "❌ FALHOU"
        print(f"{api:20} {status}")

    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMENDAÇÕES")
    print("=" * 60)

    working_apis = sum(1 for success, _ in results.values() if success)

    if results['bcb_selic'][0] and results['bcb_cdi'][0]:
        print("✅ BCB APIs funcionando - usar para SELIC e CDI")

    if results['tesouro'][0]:
        print("✅ Tesouro Direto API funcionando - usar para Tesouro IPCA+")

    if results['news'][0]:
        print("✅ Google News RSS funcionando - usar para notícias")

    if working_apis >= 3:
        print("✅ APIs suficientes para implementação inicial")
    else:
        print("⚠️  Poucas APIs funcionando - considerar scraping")

    print(f"\nAPIs funcionando: {working_apis}/5")

    return results

if __name__ == "__main__":
    results = main()