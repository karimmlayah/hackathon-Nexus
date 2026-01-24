from __future__ import annotations

import csv
import json
import os
import re
from html import unescape
from typing import Any, Dict, List, Optional


def clean_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = unescape(text)
    # Clean up whitespace
    text = " ".join(text.split())
    return text.strip()


def parse_price(price_str: str | None) -> float:
    """Parse price string to float. Returns 0.0 if invalid."""
    if not price_str:
        return 0.0
    try:
        # Remove currency symbols and whitespace
        price_str = re.sub(r"[^\d.]", "", str(price_str))
        return float(price_str) if price_str else 0.0
    except (ValueError, TypeError):
        return 0.0


def parse_bool(value: Any) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    value_str = str(value).strip().lower()
    if value_str in {"true", "1", "yes"}:
        return True
    if value_str in {"false", "0", "no"}:
        return False
    return None


def parse_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None


def parse_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None


def parse_json_list(value: Any) -> List[Any]:
    if not value:
        return []
    value_str = str(value).strip()
    if not value_str:
        return []
    if value_str.startswith("[") or value_str.startswith("{"):
        try:
            parsed = json.loads(value_str)
            return parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            return []
    return []


def extract_breadcrumbs(value: Any) -> List[str]:
    items = parse_json_list(value)
    breadcrumbs: List[str] = []
    for item in items:
        if isinstance(item, dict) and item.get("name"):
            breadcrumbs.append(str(item["name"]))
        elif isinstance(item, str):
            breadcrumbs.append(item)
    return breadcrumbs


def load_products_from_csv(csv_path: str, max_products: int | None = None) -> List[Dict[str, Any]]:
    """Load products from Amazon best sellers CSV file.
    
    Args:
        csv_path: Path to CSV file
        max_products: Maximum number of products to load (None = all)
    """
    products: List[Dict[str, Any]] = []
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            # Limit number of products if specified
            if max_products and len(products) >= max_products:
                break
            
            # Skip rows with missing essential fields
            if not row.get("name") or not row.get("name").strip():
                continue
            
            # Extract fields
            name = row.get("name", "").strip()
            brand = row.get("brandName") or row.get("brand") or ""
            brand = brand.strip() if isinstance(brand, str) else brand
            
            # Use descriptionRaw if available, otherwise description
            description = row.get("descriptionRaw") or row.get("description") or ""
            description = clean_html(description)
            
            # If description is still empty, use name as fallback
            if not description:
                description = name
            
            # Category from nodeName
            category = row.get("nodeName", "Uncategorized").strip()
            
            # Price: prefer salePrice, fallback to listedPrice
            sale_price_str = row.get("salePrice")
            listed_price_str = row.get("listedPrice")
            price_str = sale_price_str or listed_price_str
            price = parse_price(price_str)

            # Additional structured fields
            currency = (row.get("currency") or "").strip()
            rating = parse_float(row.get("rating"))
            review_count = parse_int(row.get("reviewCount"))
            in_stock = parse_bool(row.get("inStock"))
            color = (row.get("color") or "").strip()
            material = (row.get("material") or "").strip()
            mpn = (row.get("mpn") or "").strip()
            size = (row.get("size") or "").strip()
            style = (row.get("style") or "").strip()
            url = (row.get("url") or "").strip()

            breadcrumbs = extract_breadcrumbs(row.get("breadcrumbs"))
            features = parse_json_list(row.get("features"))
            image_urls = parse_json_list(row.get("imageUrls"))
            variants = parse_json_list(row.get("variants"))
            additional_properties = parse_json_list(row.get("additionalProperties"))
            gtin = parse_json_list(row.get("gtin"))

            weight = {
                "value": parse_float(row.get("weight_value")),
                "unit": (row.get("weight_unit") or "").strip(),
                "raw_unit": (row.get("weight_rawUnit") or "").strip(),
            }
            
            # ID: use sku if available, otherwise use index
            product_id = row.get("sku", "").strip() or f"amazon_{idx}"
            
            products.append(
                {
                    "id": product_id,
                    "name": name,
                    "description": description,
                    "category": category,
                    "price": price,
                    "listed_price": parse_price(listed_price_str),
                    "sale_price": parse_price(sale_price_str),
                    "currency": currency,
                    "brand": brand,
                    "rating": rating,
                    "review_count": review_count,
                    "breadcrumbs": breadcrumbs,
                    "color": color,
                    "features": features,
                    "material": material,
                    "mpn": mpn,
                    "gtin": gtin,
                    "size": size,
                    "style": style,
                    "weight": weight,
                    "in_stock": in_stock,
                    "variants": variants,
                    "current_depth": parse_int(row.get("current_depth")),
                    "new_path": (row.get("new_path") or "").strip(),
                    "additional_properties": additional_properties,
                    "image_urls": image_urls,
                    "url": url,
                }
            )
    
    return products


# Load products from Amazon CSV dataset
CSV_PATH = os.path.join(
    os.path.dirname(__file__),
    "amazon_com_best_sellers_2025_01_27",
    "amazon_com_best_sellers_2025_01_27.csv",
)

# Limit products via environment variable (useful for faster startup during testing)
# Set MAX_PRODUCTS=1000 in .env to limit to 1000 products, or leave unset for all products
max_products_env = os.getenv("MAX_PRODUCTS")
max_products = int(max_products_env) if max_products_env else None

PRODUCTS: List[Dict[str, Any]] = load_products_from_csv(CSV_PATH, max_products=max_products)

