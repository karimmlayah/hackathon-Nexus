import os
from typing import List, Dict, Any
from groq import Groq
from qdrant_client.http import models
from qdrant import get_qdrant_client, map_qdrant_product

class ChatbotService:
    def __init__(self, embedder):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.collection_name = os.getenv("QDRANT_COLLECTION", "amazon30015")
        
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables.")
            
        self.client = Groq(api_key=self.groq_api_key)
        self.qdrant_client = get_qdrant_client()
        self.embedder = embedder

    async def get_response(self, user_query: str, target_currency: str = "USD") -> Dict[str, Any]:
        """
        Full RAG pipeline: Query -> Embedding -> Qdrant Search -> LLM Prompt -> Response
        """
        # Exchange rates (approximate, mirroring frontend)
        rates = {
            "USD": 1.0,
            "EUR": 0.92,
            "TND": 3.1
        }
        currency_symbol = {
            "USD": "$",
            "EUR": "€",
            "TND": "DT"
        }
        
        rate = rates.get(target_currency, 1.0)
        symbol = currency_symbol.get(target_currency, "$")

        # 0. Check for simple greetings
        greetings = ["hi", "hello", "hey", "bonjour", "salut", "hola"]
        query_clean = user_query.lower().strip().strip("!?.")
        if query_clean in greetings:
            return {
                "answer": f"Hello! I am your FinFit assistant. How can I help you with your shopping today?",
                "products": []
            }

        try:
            # 1. Generate Query Embedding
            query_vector = self.embedder.embed_text(user_query)

            # 2. Search Qdrant directly using query_points with explicit vector name
            try:
                res = self.qdrant_client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    using="text_dense",
                    limit=5,
                    with_payload=True
                )
                search_results = res.points
                print(f"DEBUG: Found {len(search_results)} related products using 'text_dense'.")
            except Exception as search_e:
                print(f"DEBUG: Search failed: {search_e}")
                raise search_e

            # 3. Build Context & Extracted metadata
            context_parts = []
            products_metadata = []
            for point in search_results:
                try:
                    product = map_qdrant_product(point)
                    name = str(product.get('name', 'N/A'))
                    raw_price = float(product.get('price', 0))
                    raw_currency = product.get('currency', '$')
                    
                    # Normalize to USD first
                    price_usd = raw_price
                    if raw_currency == 'IDR':
                        price_usd = raw_price / 16000.0 # Approx exchange rate
                    elif raw_currency in ['EUR', '€']:
                        price_usd = raw_price * 1.09 # Approx USD/EUR
                    elif raw_currency in ['GBP', '£']:
                        price_usd = raw_price * 1.27 # Approx USD/GBP
                    
                    # Convert to Target Currency for LLM Context
                    final_price_val = price_usd * rate
                    price_display = f"{symbol}{final_price_val:.2f}"
                    
                    availability = "In Stock" if product.get('in_stock', True) else "Out of Stock"
                    image_url = product.get('image') or ""
                    url = product.get('url') or "#"
                    desc = str(product.get('description', ''))
                    
                    product_info = (
                        f"- Name: {name}\n"
                        f"  Price: {price_display}\n"
                        f"  Availability: {availability}\n"
                        f"  Description: {desc[:200]}...\n"
                    )
                    context_parts.append(product_info)
                    
                    products_metadata.append({
                        "name": name,
                        "price": price_display, # Send converted price string
                        "price_usd": price_usd, # Keep USD for frontend logic if needed
                        "availability": availability,
                        "image_url": image_url,
                        "url": url
                    })
                except Exception as inner_e:
                    print(f"DEBUG: Error building info for product: {inner_e}")
                    continue
            
            context = "\n\n".join(context_parts) if context_parts else "No specific products found for this query."
            print(f"DEBUG: Context built. Length: {len(context)}")

            # 4. Prompt Generation & LLM Call (Synchronized with rag_app)
            prompt = f"""
            You are a professional Shopping Assistant for FinFit. Your goal is to help users find the best products from our catalog.
            
            IMPORTANT: The user prefers prices in {target_currency} ({symbol}).
            All prices in the context below have already been converted to {target_currency}.
            Please use these prices in your response.

            CRITICAL RULES:
            1. USE ONLY THE PRODUCTS LISTED IN THE CONTEXT BELOW.
            2. DO NOT hallucinate products, features, or prices that are not explicitly in the context.
            3. If the context is empty or doesn't match the query, politely inform the user.
            4. Provide helpful advice for the products you recommend.
            5. Keep your tone friendly, helpful, and professional.
            6. Use markdown for better readability.

            PRODUCT CONTEXT:
            {context}

            USER QUESTION:
            {user_query}

            ASSISTANT ANSWER:
            """

            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                model=self.groq_model,
                temperature=0.0,
            )

            return {
                "answer": chat_completion.choices[0].message.content,
                "products": products_metadata
            }

        except Exception as e:
            import traceback
            print(f"DEBUG: Error in RAG pipeline: {str(e)}")
            traceback.print_exc()
            return "I'm sorry, I'm having trouble connecting to my knowledge base right now. Please try again in a moment!"
