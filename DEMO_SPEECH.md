# FinFit — Demo Speech (English)

**Duration:** ~1 minute

---

"Hello. **FinFit** is an e-commerce demo for electronics. I’ll walk you through the main parts.

**Search engine.** You can search in two ways. First, by **text**: you type a query like *'cheapest headphones'* or *'laptop under 500 dollars'*. The system uses **semantic search**: it embeds your query and finds the most similar products in a vector database, so results match meaning, not just keywords. Second, you can search by **image**: you upload a photo — for example of a product you like — and optionally add text. The same engine combines the image and the text to find similar items. So the search is **multimodal**: text and image together.

**RAG — the AI assistant.** The chat uses **Retrieval-Augmented Generation**. When you ask a question, the system first **retrieves** relevant products from the catalog using the search engine. Then an **LLM** takes that context and your question to generate a short answer and the product cards you see. So the assistant doesn’t invent products; it grounds its answer in real catalog data.

**Recommendations.** The *Recommandé pour vous* section is personalized. It uses your **wishlist**, your **cart**, and your **browsing history** to build a profile and recommend products similar to what you liked or viewed. The more you interact, the better the suggestions.

**Login.** You can sign in to save your **wishlist** and **cart** across sessions. Login also lets the system tie your actions to your account, so recommendations and the assistant can use your full history.

That’s FinFit: semantic and multimodal search, RAG in the chat, personalized recommendations, and login to keep your data. Thank you."
