"""
Stock Universe Definitions
==========================

Defines the stock universes for the strategy package.
Includes S&P 500, NASDAQ 100, ASX 200, Russell 2000, and ETFs.

This module provides:
- Individual getter functions for each universe
- A central UNIVERSE_REGISTRY with metadata
- A unified get_universe_tickers() function
"""

from typing import List, Dict, Any, Callable, Optional
import requests
import pandas as pd
from io import StringIO
import functools


# ============== Individual Universe Getters ==============

@functools.lru_cache(maxsize=1)
def get_sp500_tickers() -> List[str]:
    """Get S&P 500 tickers from GitHub (cached)."""
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        sp500_df = pd.read_csv(StringIO(response.text))
        return sorted(list(set(sp500_df['Symbol'].str.replace('.', '-', regex=False).tolist())))
    except Exception as e:
        print(f"⚠️ Failed to fetch S&P 500 from GitHub: {e}")
        # Fallback to top 50 constituents
        return [
            "AAPL", "MSFT", "AMZN", "GOOG", "GOOGL", "META", "TSLA", "NVDA", "BRK-B", "JPM",
            "V", "UNH", "HD", "MA", "PG", "XOM", "CVX", "JNJ", "LLY", "ABBV",
            "BAC", "PFE", "KO", "COST", "WMT", "MRK", "DIS", "CSCO", "PEP", "TMO",
            "ABT", "AVGO", "VZ", "ACN", "MCD", "ADBE", "CRM", "NKE", "CMCSA", "TXN",
            "DHR", "NEE", "WFC", "ORCL", "LIN", "BMY", "UPS", "PM", "QCOM", "RTX"
        ]


@functools.lru_cache(maxsize=1)
def get_nasdaq100_tickers() -> List[str]:
    """Get NASDAQ 100 tickers."""
    # Top 100 NASDAQ constituents
    return [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "COST",
        "PEP", "ADBE", "CSCO", "NFLX", "TMUS", "AMD", "CMCSA", "INTC", "INTU", "TXN",
        "QCOM", "HON", "AMGN", "AMAT", "BKNG", "ISRG", "SBUX", "MDLZ", "GILD", "ADI",
        "PDD", "VRTX", "LRCX", "ADP", "REGN", "PANW", "KLAC", "MU", "SNPS", "CDNS",
        "ASML", "MELI", "PYPL", "MRVL", "CHTR", "MAR", "ORLY", "NXPI", "CSX", "ABNB",
        "CEG", "CTAS", "PCAR", "FTNT", "WDAY", "MNST", "CPRT", "AEP", "DXCM", "PAYX",
        "KDP", "AZN", "ODFL", "MCHP", "ROST", "KHC", "EXC", "ADSK", "FAST", "LULU",
        "MRNA", "VRSK", "EA", "BKR", "IDXX", "GEHC", "CTSH", "CDW", "FANG", "CSGP",
        "BIIB", "ON", "ANSS", "XEL", "DDOG", "ZS", "GFS", "TEAM", "TTWO", "ILMN",
        "WBD", "ZM", "WBA", "DLTR", "LCID", "JD", "RIVN", "SIRI", "ALGN", "ENPH"
    ]


@functools.lru_cache(maxsize=1)
def get_russell2000_tickers() -> List[str]:
    """Get Russell 2000 tickers (representative sample of ~100 small-cap stocks)."""
    # Representative sample - full list would need external data source
    return [
        "AMC", "BBBY", "GME", "SPCE", "PLTR", "SOFI", "HOOD", "TLRY", "SNDL", "NIO",
        "LCID", "RIVN", "FSR", "GOEV", "NKLA", "WKHS", "RIDE", "HYLN", "ARVL", "REE",
        "PLUG", "FCEL", "BLDP", "BE", "BLOOM", "CHPT", "EVGO", "BLNK", "DCFC", "SES",
        "STEM", "RUN", "NOVA", "ARRY", "MAXN", "SEDG", "ENPH", "TAN", "SHLS", "FTCI",
        "ASTS", "SPIR", "RDW", "RKLB", "LLAP", "SATL", "MNTS", "ASTR", "VORB", "LUNR",
        "IONQ", "RGTI", "QUBT", "QBTS", "ARQQ", "QMCO", "IONQ", "QTUM", "QRVO", "QUIK",
        "PATH", "UPST", "AFRM", "LMND", "ROOT", "HIPO", "OSCAR", "CLVR", "MILE", "NEXT",
        "COIN", "MARA", "RIOT", "CLSK", "BITF", "BTBT", "HUT", "CIFR", "IREN", "BTDR",
        "MSTR", "GBTC", "ARKK", "ARKF", "ARKW", "ARKG", "ARKQ", "ARKX", "PRNT", "IZRL",
        "VET", "OVV", "MTDR", "PR", "CIVI", "CHRD", "FANG", "VTLE", "CRGY", "BATL"
    ]


def get_us_etfs() -> List[str]:
    """Get US ETFs for portfolio construction."""
    return [
        "SPY", "QQQ", "IWM", "DIA", "VTI",  # Broad market
        "GLD", "SLV", "IAU", "SGOL", "GLDM",  # Precious metals
        "TLT", "IEF", "SHY", "BND", "AGG",  # Fixed income
        "EEM", "VWO", "IEMG", "VEA", "EFA",  # International
        "XLF", "XLK", "XLE", "XLV", "XLI",  # Sectors
        "VNQ", "IYR", "XLRE", "RWR", "SCHH",  # Real estate
        "USO", "UNG", "DBC", "GSG", "PDBC",  # Commodities
        "VXX", "UVXY", "SVXY", "VIXY", "VIXM"  # Volatility
    ]


@functools.lru_cache(maxsize=1)
def get_asx200_tickers() -> List[str]:
    """Get ASX 200 tickers (top AU stocks)."""
    return [
        "BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "WES.AX", "MQG.AX",
        "WOW.AX", "TLS.AX", "RIO.AX", "FMG.AX", "WDS.AX", "GMG.AX", "TCL.AX", "STO.AX",
        "QBE.AX", "SUN.AX", "IAG.AX", "AMC.AX", "COL.AX", "ORG.AX", "APA.AX", "REA.AX",
        "ALL.AX", "BXB.AX", "JHX.AX", "NCM.AX", "S32.AX", "ORI.AX", "ASX.AX", "XRO.AX",
        "CPU.AX", "QAN.AX", "SHL.AX", "RHC.AX", "MPL.AX", "AZJ.AX", "DXS.AX", "SGP.AX",
        "MIN.AX", "NST.AX", "EVN.AX", "NHC.AX", "WHC.AX", "YAL.AX", "SFR.AX", "OZL.AX",
        "BOQ.AX", "BEN.AX"
    ]


def get_asx_total_tickers() -> List[str]:
    """Get extended ASX universe (ASX 200 + mid-caps)."""
    asx200 = get_asx200_tickers()
    mid_caps = [
        "ALQ.AX", "ALD.AX", "ALU.AX", "AWC.AX", "BKW.AX", "BSL.AX", "CGF.AX", "CIM.AX",
        "CWY.AX", "DDR.AX", "ELD.AX", "EVT.AX", "FPH.AX", "GNC.AX", "GUD.AX", "HVN.AX",
        "IEL.AX", "IGO.AX", "ILU.AX", "IPL.AX", "LYC.AX", "MGR.AX", "NEC.AX", "NUF.AX",
        "ORA.AX", "OSH.AX", "PBH.AX", "PLS.AX", "PME.AX", "PMV.AX", "PPT.AX", "PRN.AX",
        "PXA.AX", "REH.AX", "RGN.AX", "RWC.AX", "SDR.AX", "SEK.AX", "SGM.AX", "SKC.AX",
        "SRL.AX", "STO.AX", "SUL.AX", "SWM.AX", "TAH.AX", "TGR.AX", "TPG.AX", "TWE.AX",
        "VCX.AX", "WGN.AX"
    ]
    return sorted(list(set(asx200 + mid_caps)))


def get_asx_etfs() -> List[str]:
    """Get ASX-listed ETFs."""
    return [
        "VAS.AX", "VGS.AX", "STW.AX", "IOZ.AX", "IVV.AX",  # Broad market
        "VTS.AX", "VEU.AX", "VHY.AX", "VAE.AX", "VAP.AX",  # Vanguard
        "A200.AX", "ASIA.AX", "NDQ.AX", "ETHI.AX", "FAIR.AX",  # BetaShares
        "GOLD.AX", "QAU.AX", "PMGOLD.AX", "GDX.AX", "NUGG.AX",  # Gold
        "HBRD.AX", "BOND.AX", "GOVT.AX", "IAF.AX", "RGB.AX"  # Fixed income
    ]


def get_core_etfs() -> List[str]:
    """Get core ETFs for simple portfolio construction."""
    return get_us_etfs()[:10] + get_asx_etfs()[:5]


def get_screener_universe() -> List[str]:
    """Get the full screener universe."""
    return sorted(list(set(get_sp500_tickers() + get_us_etfs() + get_asx200_tickers())))


# ============== Universe Registry ==============

UNIVERSE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "SPX500": {
        "name": "S&P 500",
        "description": "500 largest US companies by market cap",
        "region": "US",
        "asset_class": "equity",
        "getter": get_sp500_tickers,
    },
    "NASDAQ100": {
        "name": "NASDAQ 100",
        "description": "100 largest non-financial NASDAQ companies",
        "region": "US",
        "asset_class": "equity",
        "getter": get_nasdaq100_tickers,
    },
    "RUSSELL2000": {
        "name": "Russell 2000",
        "description": "Small-cap US stocks (representative sample)",
        "region": "US",
        "asset_class": "equity",
        "getter": get_russell2000_tickers,
    },
    "US_ETFS": {
        "name": "US ETFs",
        "description": "Broad US-listed ETFs across asset classes",
        "region": "US",
        "asset_class": "etf",
        "getter": get_us_etfs,
    },
    "ASX200": {
        "name": "ASX 200",
        "description": "200 largest Australian companies",
        "region": "AU",
        "asset_class": "equity",
        "getter": get_asx200_tickers,
    },
    "ASX_TOTAL": {
        "name": "ASX Total Market",
        "description": "Extended Australian market including mid-caps",
        "region": "AU",
        "asset_class": "equity",
        "getter": get_asx_total_tickers,
    },
    "ASX_ETFS": {
        "name": "ASX ETFs",
        "description": "Australian-listed ETFs",
        "region": "AU",
        "asset_class": "etf",
        "getter": get_asx_etfs,
    },
    "CORE_ETFS": {
        "name": "Core ETFs",
        "description": "Essential ETFs for portfolio construction",
        "region": "GLOBAL",
        "asset_class": "etf",
        "getter": get_core_etfs,
    },
}


# ============== Unified Universe Access ==============

def get_universe_tickers(universe_key: str) -> List[str]:
    """
    Get tickers for a given universe key.
    
    Args:
        universe_key: Key from UNIVERSE_REGISTRY (e.g., 'SPX500', 'NASDAQ100')
    
    Returns:
        List of ticker symbols
    
    Raises:
        ValueError: If universe_key is not found in registry
    """
    if universe_key not in UNIVERSE_REGISTRY:
        available = list(UNIVERSE_REGISTRY.keys())
        raise ValueError(f"Unknown universe '{universe_key}'. Available: {available}")
    
    getter = UNIVERSE_REGISTRY[universe_key]["getter"]
    return getter()


def get_universe_info(universe_key: str) -> Dict[str, Any]:
    """
    Get metadata for a universe.
    
    Args:
        universe_key: Key from UNIVERSE_REGISTRY
    
    Returns:
        Dict with name, description, region, asset_class, and ticker_count
    """
    if universe_key not in UNIVERSE_REGISTRY:
        available = list(UNIVERSE_REGISTRY.keys())
        raise ValueError(f"Unknown universe '{universe_key}'. Available: {available}")
    
    info = UNIVERSE_REGISTRY[universe_key].copy()
    # Remove the getter function from the response
    getter = info.pop("getter")
    # Add ticker count
    info["ticker_count"] = len(getter())
    info["key"] = universe_key
    return info


def list_universes() -> List[Dict[str, Any]]:
    """
    List all available universes with metadata.
    
    Returns:
        List of universe info dicts (excludes getter functions)
    """
    return [get_universe_info(key) for key in UNIVERSE_REGISTRY.keys()]
