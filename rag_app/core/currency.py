"""
Currency conversion service
"""

# Exchange rates (1 USD = X units of currency)
EXCHANGE_RATES = {
    "USD": 1.0,
    "TND": 3.15,  # 1 USD = 3.15 TND (approximate)
    "IDR": 15800,  # 1 USD = 15800 IDR (approximate)
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 150,
    "AUD": 1.54,
    "CAD": 1.36,
}

TND_RATE = EXCHANGE_RATES.get("TND", 3.15)  # 1 USD = 3.15 TND

def convert_to_tnd(price: float, from_currency: str = "USD") -> float:
    """
    Convert any price to Tunisian Dinar (TND)
    
    Args:
        price: The price amount
        from_currency: Currency code (USD, IDR, EUR, etc.)
    
    Returns:
        Price in TND
    """
    from_currency = from_currency.upper()
    
    # If price is in TND, return as is
    if from_currency == "TND":
        return price
    
    # Get exchange rate for source currency
    rate = EXCHANGE_RATES.get(from_currency, 1.0)
    
    # Convert to USD first, then to TND
    price_in_usd = price / rate if rate > 0 else price
    price_in_tnd = price_in_usd * TND_RATE
    
    return round(price_in_tnd, 2)

def format_price_tnd(price: float, currency: str = "USD") -> str:
    """
    Format price in TND for display
    
    Args:
        price: Price amount
        currency: Source currency
    
    Returns:
        Formatted string like "750.45 DT"
    """
    price_tnd = convert_to_tnd(price, currency)
    return f"{price_tnd:,.2f} DT"

def detect_currency(price_str: str) -> str:
    """
    Try to detect currency from price string or metadata
    
    Args:
        price_str: Price string like "238.2" or "7,299,000"
    
    Returns:
        Currency code
    """
    # If price is very large (> 1000), likely IDR or similar
    try:
        price = float(price_str.replace(",", ""))
        if price > 1000:
            return "IDR"  # Large numbers are typically IDR
    except:
        pass
    
    return "USD"  # Default to USD
