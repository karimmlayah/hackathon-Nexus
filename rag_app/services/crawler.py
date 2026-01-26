import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from services.ingestion import chunk_text

def scrape_url(url: str) -> List[Dict]:
    """
    Scrapes a URL and returns chunks.
    Simple implementation using requests and BeautifulSoup.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        title = soup.title.string if soup.title else url
        
        chunks = chunk_text(text)
        documents = []
        
        for chunk in chunks:
            documents.append({
                "text": chunk,
                "source": url,
                "title": title,
                "type": "web"
            })
            
        return documents
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []
