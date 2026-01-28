from data import PRODUCTS
from collections import Counter

categories = [p.get('category') for p in PRODUCTS]
category_counts = Counter(categories)

print("Actual Categories in CSV:")
for cat, count in category_counts.most_common(20):
    print(f"{cat}: {count}")
