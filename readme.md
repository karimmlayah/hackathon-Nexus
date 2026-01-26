# FinCommerce – Context-Aware E-Commerce Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![AI Powered](https://img.shields.io/badge/AI-Qdrant%20%7C%20RAG-blue?style=flat-square)](#)
[![Web Platform](https://img.shields.io/badge/Web-FrontOffice%20%7C%20BackOffice-green?style=flat-square)](#)

![FinCommerce Platform](les_images/cover.png)

FinCommerce is an **intelligent e-commerce platform** designed to enhance product discovery
through **semantic search**, **image-based search**, and an **AI-powered RAG chatbot**.
The system also integrates a **financial-awareness layer**, enabling recommendations
that are aligned with user budgets and preferences.

---

## Table of Contents

- [Features](#features)
- [Interfaces](#interfaces)
- [Architecture](#architecture)
- [Technologies](#technologies)
- [Installation](#installation)
- [Usage](#usage)

---

## Features


- Modern design with purple gradient
- Real-time search
- Multilingual support (English, French, Arabic)
- Similarity score displayed for each result
- Clickable examples for quick testing
- Responsive and mobile-friendly
- Results show category and price


---

## Interfaces

### Front-Office
![Front Office](les_images/frontoffice.png)

**Description:**  
The Front-Office allows users to browse the product catalog, perform intelligent searches,
and interact with the AI chatbot. Smooth and intuitive UX is prioritized.

### Semantic & Multimodal Search
![Semantic Search](les_images/semantic_search.png)

**Description:**  
Enables natural language queries and image-based discovery. Semantic and visual understanding improves product relevance.

### AI Chatbot (RAG)
![Chatbot](les_images/chatbot.png)
![Chatbot](les_images/architecture.gif)

**Description:**  
Combines Qdrant vector retrieval with generative AI to provide contextual, financially-aware responses.



---

## Architecture
![Architecture](les_images/architecture.webp)

**Description:**   
The platform consists of five main layers:

1. **Presentation Layer** – Front-Office & Back-Office  
2. **Intelligence Layer** – Semantic Search, Image Search, RAG Chatbot  
3. **Recommendation Layer** – Smart recommendations, query-less suggestions, financial-aware filtering  
4. **Vector Storage Layer** – Qdrant Cloud (embeddings + metadata)  
5. **Data & Model Layer** – Embedding Models & Product Dataset  

Qdrant stores text, image embeddings, and metadata for efficient similarity search and hybrid retrieval.

---

## Technologies

| Catégorie           | Technologie / Outil                   | Description Courte                   |
|--------------------|--------------------------------------|------------------------------------|
| Frontend           | HTML, CSS, JavaScript, Bootstrap      | Interfaces web réactives           |
| Backend            | Python (FastAPI / Flask)              | API et logique serveur              |
| AI & NLP           | Transformers, Vision-Language Models  | Recherche sémantique et embeddings |
| Vector Database    | Qdrant Cloud                           | Stockage et recherche vectorielle  |
| Data               | CSV, Pandas                            | Gestion des datasets produits       |
| Embeddings         | all-MiniLM-16-v2, splade, CLIP        | Textes et images multimodaux       |
| RAG Chatbot        | Langage & retrieval pipeline          | Génération augmentée par récupération |
| Dev & Environnement| Git, venv, pip                         | Gestion de projet et dépendances   |

---

## Installation

```bash
git clone https://github.com/karimmlayah/hackathon-Nexus
cd hackathon-Nexus-main
cd d:\template
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload --port 8001

```
---

## Usage


### Front-Office (User)
1. Open the interface in your browser:  
   - Go to [http://localhost:8001/](http://localhost:8001/)  
   - Or directly: [http://localhost:8001/static/search.html](http://localhost:8001/static/search.html)
2. Browse the product catalog or use the **semantic search bar** to find items.
3. **Test search queries** with examples:  
   - English: `wireless headphones`, `coffee maker`, `laptop backpack`, `smart watch`  
   - French: `machine espresso`, `casque bluetooth`, `sac à dos ordinateur`
4. **View search results**:  
   Each product displays:  
   - Product Name  
   - Similarity Score (0-100%)  
   - Category  
   - Description  
   - Price  
   - Product ID
5. Use image-based search to find visually similar products.
6. Interact with the **RAG chatbot** for personalized recommendations based on preferences and budget.
7. Apply financial filters to display only products within your price range

