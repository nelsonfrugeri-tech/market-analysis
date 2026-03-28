"""Tesouro Nacional API client for benchmark data collection."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional
from urllib.request import Request, urlopen

from .data_models import TesouroTitleData

logger = logging.getLogger(__name__)

TESOURO_API_BASE = "https://www.tesourotransparente.gov.br/ckan/dataset/"
TESOURO_PRECOS_TAXAS_URL = f"{TESOURO_API_BASE}df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precos_e_taxas_de_titulos_publicos.csv"

DEFAULT_TIMEOUT = 30


class TesouroFetchError(Exception):
    """Raised when Tesouro Nacional API fetch fails."""


def fetch_tesouro_data(
    start_date: date,
    end_date: date,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[TesouroTitleData]:
    """Fetch Tesouro Nacional title data from CSV endpoint.

    Args:
        start_date: Period start (inclusive).
        end_date: Period end (inclusive).
        timeout: HTTP timeout in seconds.

    Returns:
        List of TesouroTitleData objects.
    """
    logger.info("Fetching Tesouro Nacional data: %s to %s", start_date, end_date)

    try:
        req = Request(
            TESOURO_PRECOS_TAXAS_URL,
            headers={"User-Agent": "MarketAnalysis/1.0"}
        )

        with urlopen(req, timeout=timeout) as resp:
            csv_content = resp.read().decode("utf-8")

        # Parse CSV and filter by date range
        lines = csv_content.strip().split('\n')
        if not lines:
            raise TesouroFetchError("Empty response from Tesouro API")

        header = lines[0].split(';')
        data = []

        for line in lines[1:]:
            if not line.strip():
                continue

            fields = line.split(';')
            if len(fields) < len(header):
                continue

            try:
                # Parse date from "Vencimento do Titulo" field
                vencimento_str = fields[1]  # Assuming second column is maturity
                data_base_str = fields[0]   # Assuming first column is base date

                # Convert date strings (DD/MM/YYYY format)
                data_base = datetime.strptime(data_base_str, "%d/%m/%Y").date()
                vencimento = datetime.strptime(vencimento_str, "%d/%m/%Y").date()

                # Filter by date range
                if not (start_date <= data_base <= end_date):
                    continue

                # Extract relevant fields (adjust indices based on actual CSV structure)
                title_code = fields[2] if len(fields) > 2 else ""
                title_name = fields[3] if len(fields) > 3 else ""

                # Parse rates (replace comma with dot for float conversion)
                interest_rate_str = fields[4].replace(",", ".") if len(fields) > 4 else "0"
                parity_price_str = fields[5].replace(",", ".") if len(fields) > 5 else "0"

                interest_rate = float(interest_rate_str) if interest_rate_str else 0.0
                parity_price = float(parity_price_str) if parity_price_str else 0.0

                title_data = TesouroTitleData(
                    date=data_base,
                    title_code=title_code,
                    title_name=title_name,
                    maturity_date=vencimento,
                    interest_rate=interest_rate,
                    parity_price=parity_price,
                )

                data.append(title_data)

            except (ValueError, IndexError) as e:
                logger.warning("Failed to parse Tesouro line: %s - %s", line, e)
                continue

        logger.info("Parsed %d Tesouro records", len(data))
        return data

    except Exception as exc:
        raise TesouroFetchError(f"Failed to fetch Tesouro data: {exc}") from exc


def get_selic_rates(
    tesouro_data: list[TesouroTitleData],
    title_filter: str = "Tesouro Selic"
) -> dict[date, float]:
    """Extract SELIC rates from Tesouro data.

    Args:
        tesouro_data: List of TesouroTitleData.
        title_filter: Filter string for SELIC titles.

    Returns:
        Dict mapping dates to SELIC rates (%).
    """
    selic_rates = {}

    for title in tesouro_data:
        if title_filter.lower() in title.title_name.lower():
            # For Tesouro SELIC, the interest rate represents the SELIC rate
            selic_rates[title.date] = title.interest_rate

    return selic_rates


def get_ipca_plus_rates(
    tesouro_data: list[TesouroTitleData],
    title_filter: str = "IPCA+"
) -> dict[date, float]:
    """Extract IPCA+ rates from Tesouro data.

    Args:
        tesouro_data: List of TesouroTitleData.
        title_filter: Filter string for IPCA+ titles.

    Returns:
        Dict mapping dates to IPCA+ rates (%).
    """
    ipca_rates = {}

    for title in tesouro_data:
        if title_filter in title.title_name:
            # IPCA+ titles show real interest rate above IPCA
            ipca_rates[title.date] = title.interest_rate

    return ipca_rates