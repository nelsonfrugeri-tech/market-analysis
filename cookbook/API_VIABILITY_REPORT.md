# Technical Viability Report - Data Sources for Market Analysis

> Generated at: 2026-03-27
> Purpose: Evaluate free data sources for daily fund monitoring system
> Focus: Nu Reserva Planejada (CNPJ 43.121.002/0001-41)

---

## Executive Summary

**Verdict: VIABLE** - All critical data needs can be met with free APIs.

| Source | Status | Auth Required | Reliability | Priority |
|---|---|---|---|---|
| BCB API (SGS) | Working | No | High (government) | Primary |
| CVM Dados Abertos | Working | No | High (government) | Primary |
| Google News RSS | Working | No | Medium | Primary |
| NewsAPI | Working | Yes (paid) | High | Optional |
| MaisRetorno | Accessible | No (scraping) | Low (fragile) | Fallback |
| Yahoo Finance | Partial | No | Medium | Fallback |
| Tesouro Direto API | Broken | - | - | Excluded |

---

## 1. API BCB (Banco Central do Brasil)

### Viability: CONFIRMED

**Base endpoint:** `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{SERIE}/dados`

**Parameters:**
- `formato=json` (also supports csv)
- `dataInicial=DD/MM/YYYY`
- `dataFinal=DD/MM/YYYY`

### Series Codes

| Indicator | Series Code | Frequency | Tested |
|---|---|---|---|
| SELIC target | 432 | Daily | Yes - 31 records/month |
| CDI | 4389 | Daily (business days) | Yes - 22 records/month |
| IPCA | 433 | Monthly | Yes - working |
| SELIC rate | 11 | Daily | Available |
| IGP-M | 189 | Monthly | Available |
| Dollar (PTAX) | 1 | Daily | Available |

### Response Format
```json
[
  {"data": "27/03/2026", "valor": "14.75"}
]
```

### Technical Notes
- No authentication required
- No documented rate limits for reasonable usage (1x/day is fine)
- Date format in response is DD/MM/YYYY (needs parsing)
- Values are strings (need float conversion)
- Empty array returned for invalid date ranges (no error)
- Python library available: `python-bcb` (pip install python-bcb) wraps SGS into pandas DataFrames
- Alternative library: `sgs` (pip install sgs)

### Recommended Usage
```python
# Direct HTTP (minimal deps)
url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados"
params = {"formato": "json", "dataInicial": "01/03/2026", "dataFinal": "27/03/2026"}

# Or via python-bcb
from bcb import sgs
df = sgs.get({"SELIC": 432, "CDI": 4389, "IPCA": 433}, start="2026-01-01")
```

### Risk Assessment
- **Low risk** - Government API, stable since 2010+
- Occasional downtime during BCB maintenance windows (weekends)

---

## 2. CVM Dados Abertos (Fundos de Investimento)

### Viability: CONFIRMED

**Portal:** `https://dados.cvm.gov.br/dataset/fi-doc-inf_diario`

### Data Structure

The CVM publishes daily fund reports (Informe Diario) as CSV files organized by month:

**URL pattern:** `https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{YYYYMM}.zip`

Each CSV contains ALL Brazilian funds for that month. Key columns:

| Column | Description |
|---|---|
| CNPJ_FUNDO | Fund CNPJ |
| DT_COMPTC | Reference date |
| VL_TOTAL | Total portfolio value |
| VL_QUOTA | Share value (NAV) |
| VL_PATRIM_LIQ | Net equity |
| CAPTC_DIA | Daily inflows |
| RESG_DIA | Daily redemptions |
| NR_COTST | Number of shareholders |
| TP_FUNDO | Fund type (new field) |

### Nu Reserva Planejada Identification
- **CNPJ:** 43.121.002/0001-41
- **Full name:** NU RESERVA PLANEJADA FUNDO DE INVESTIMENTO FINANCEIRO DA CIC RENDA FIXA CRED PRIV RESP LIMITADA
- **Type:** Renda Fixa (Fixed Income), Credit Privado
- **Manager:** Nu Asset Management

### Fund Registration Data
- **URL:** `https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv`
- Contains fund metadata (name, CNPJ, manager, admin, type, status)
- Can be used to map CNPJ to fund name

### Technical Notes
- Files are CSV compressed as ZIP
- Monthly files can be 50-200 MB uncompressed (all BR funds)
- Current + previous month files updated daily at 08:00h
- Historical data available for last 12 months on portal
- Older data available at: `https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/HIST/`
- Resolution CVM 175 (2025) added new fields (TP_FUNDO, class/subclass structure)

### Recommended Approach
```python
import pandas as pd
import io, zipfile, requests

url = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_202603.zip"
response = requests.get(url)
with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    with z.open(z.namelist()[0]) as f:
        df = pd.read_csv(f, sep=";", encoding="latin-1")

# Filter Nu Reserva Planejada
nu_fund = df[df["CNPJ_FUNDO"] == "43.121.002/0001-41"]
```

### Risk Assessment
- **Low risk** - Government data, legally mandated disclosure
- Large file sizes require filtering strategy (download full, filter locally)
- CSV format may change with regulatory updates (CVM 175 transition)

---

## 3. Google News RSS

### Viability: CONFIRMED

**Endpoint:** `https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419`

### Parameters
| Parameter | Value | Description |
|---|---|---|
| q | URL-encoded query | Search terms (e.g., "Nubank", "Nu+Reserva+Planejada") |
| hl | pt-BR | Language |
| gl | BR | Country |
| ceid | BR:pt-419 | Content edition |

### Response Format
- XML/RSS feed
- Contains `<item>` elements with: `<title>`, `<link>`, `<pubDate>`, `<description>`, `<source>`
- Typically returns up to 100 articles per query

### Tested Queries
- `q=Nubank` -> 100 articles returned
- `q=Nu+Reserva+Planejada` -> relevant for specific fund news
- `q=Nubank+fundos` -> broader fund-related news

### Technical Notes
- No authentication, no API key
- No official rate limit documented, but Google may block aggressive scraping
- RSS format is stable and well-supported
- `feedparser` library recommended for parsing
- No official API -- this is an undocumented but long-standing RSS endpoint
- Articles include source attribution (which news outlet)

### Recommended Usage
```python
import feedparser

url = "https://news.google.com/rss/search?q=Nubank&hl=pt-BR&gl=BR&ceid=BR:pt-419"
feed = feedparser.parse(url)
for entry in feed.entries[:10]:
    print(f"{entry.published}: {entry.title} ({entry.source.title})")
```

### Risk Assessment
- **Medium risk** - Undocumented endpoint, Google could change/block it
- Quality varies (blogs, press releases mixed with serious journalism)
- Sufficient for daily context; not for quantitative analysis

---

## 4. NewsAPI

### Viability: CONFIRMED (requires paid key)

**Endpoint:** `https://newsapi.org/v2/everything`

### Pricing
- **Developer (free):** 100 requests/day, articles up to 1 month old, no commercial use
- **Business:** $449/month

### Technical Notes
- Returns structured JSON with title, description, content, source, publishedAt
- Better quality filtering than Google News RSS
- Free tier is very limited (100 req/day, 1-month history, dev only)

### Verdict
- **Not recommended for this project** - Free tier too limited, paid tier too expensive
- Google News RSS covers the news requirement adequately for daily monitoring

---

## 5. MaisRetorno (Scraping)

### Viability: POSSIBLE BUT NOT RECOMMENDED AS PRIMARY

**Website:** `https://maisretorno.com`
**Fund page:** `https://maisretorno.com/fundo/nu-reserva-planejada-fif-da-cic-rf-cp-rl`

### What's Available
- Fund performance data, charts, comparisons
- Rankings and analysis
- MaisRetorno offers a paid API (`lp.maisretorno.com/api`) for programmatic access

### Technical Notes
- Scraping is fragile (HTML structure changes break scrapers)
- No robots.txt exclusion found for fund pages, but ToS may prohibit scraping
- JavaScript-rendered content may require Selenium/Playwright
- Rate limiting likely present but undocumented

### Verdict
- **Use only as fallback** if CVM data is insufficient
- CVM provides the same core data (NAV, equity, flows) officially
- If performance comparison features are needed, consider MaisRetorno paid API

---

## 6. Yahoo Finance

### Viability: PARTIAL

**Endpoint:** `https://query1.finance.yahoo.com/v8/finance/chart/{TICKER}.SA`

### Results
- Brazilian stocks (e.g., PETR4.SA): Working
- Treasury ETFs (TREA11.SA): Ticker not found
- Fund data: Not available (Brazilian mutual funds are not listed on Yahoo)

### Verdict
- **Not useful for this project** - Nu Reserva Planejada is not a traded ETF
- Could be used for stock market context if needed later

---

## 7. Tesouro Direto API

### Viability: NOT AVAILABLE

- Historical API endpoint returned 400 errors
- DNS resolution issues on some Tesouro Nacional endpoints
- No public REST API currently available

### Alternative
- BCB IPCA series (433) serves as proxy for Tesouro IPCA+ benchmark
- BCB SELIC series (432) covers Tesouro Selic benchmark

---

## Recommended Architecture

### Data Pipeline (Daily, 1x/day)

```
[1] BCB API (SGS)          --> SELIC, CDI, IPCA rates
[2] CVM Dados Abertos      --> Nu Reserva Planejada NAV, equity, flows
[3] Google News RSS         --> Nubank news context
                |
                v
        [SQLite Database]
                |
                v
        [PDF Report Generator]
```

### Dependency Stack (Minimal)

| Library | Purpose | PyPI |
|---|---|---|
| httpx | Async HTTP client | httpx |
| pandas | CSV processing (CVM data) | pandas |
| feedparser | RSS parsing (Google News) | feedparser |
| reportlab | PDF generation | reportlab |
| sqlite3 | Local DB | stdlib |
| python-bcb | BCB data helper (optional) | python-bcb |

### Key Technical Decisions

1. **httpx over requests** - Async support, connection pooling, modern API
2. **pandas for CVM only** - CVM CSVs are large and need efficient filtering
3. **SQLite** - Local, zero-config, sufficient for daily data of 1 fund
4. **feedparser** - Battle-tested RSS parser, handles edge cases

### Data Freshness

| Source | Update Frequency | Lag |
|---|---|---|
| BCB SELIC/CDI | Daily (business days) | Same day |
| BCB IPCA | Monthly | ~15 days after month end |
| CVM Informe Diario | Daily at 08:00h | T+1 (previous business day) |
| Google News | Real-time | Minutes |

---

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| BCB API downtime | Low | High | Cache last known values, retry with backoff |
| CVM CSV format change | Low | Medium | Schema validation on download, alert on mismatch |
| Google News RSS blocked | Medium | Low | GNews API free tier (100 req/day) as backup |
| Large CVM file download | Certain | Low | Download once/day, filter in memory, cache locally |
| Nu Reserva Planejada CNPJ change | Very low | High | Use CVM cadastro to validate CNPJ periodically |

---

## Next Steps

1. **Implement BCB data collector** - Simplest, highest value
2. **Implement CVM data collector** - Core fund data
3. **Implement Google News collector** - Context layer
4. **Design SQLite schema** - Store daily snapshots
5. **Build PDF report** - Daily output

---

## Sources

- [BCB SGS Documentation](https://wilsonfreitas.github.io/python-bcb/sgs.html)
- [BCB SGS Web Service PDF](http://catalogo.governoeletronico.gov.br/arquivos/Documentos/WS_SGS_BCB.pdf)
- [python-bcb on PyPI](https://pypi.org/project/python-bcb/)
- [CVM Dados Abertos - Fundos](https://dados.cvm.gov.br/group/fundos-de-investimento)
- [CVM Informe Diario](https://dados.cvm.gov.br/dataset/fi-doc-inf_diario)
- [CVM Portal News - CVM 175 Updates](https://www.gov.br/cvm/pt-br/assuntos/noticias/2025/portal-dados-abertos-cvm-traz-novidades-nas-informacoes-sobre-fundos-de-investimento)
- [Nu Reserva Planejada - Nu Asset](https://www.nuasset.nu/fundo/nu-reserva-planejada/)
- [Nu Reserva Planejada - MaisRetorno](https://maisretorno.com/fundo/nu-reserva-planejada-fif-da-cic-rf-cp-rl)
- [Google News RSS Alternatives Guide](https://scrapfly.io/blog/posts/guide-to-google-news-api-and-alternatives)
- [Free News APIs 2026](https://newsdata.io/blog/best-free-news-api/)
- [MaisRetorno API](https://lp.maisretorno.com/api)
