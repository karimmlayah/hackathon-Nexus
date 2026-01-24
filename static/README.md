# Interface de Test - Smart Semantic Search

Interface web moderne et intuitive pour tester la recherche sémantique sur 25,000+ produits Amazon.

## 🎨 Fonctionnalités

- ✨ Design moderne avec gradient violet
- 🔍 Recherche en temps réel
- 🌍 Support multilingue (English, French, Arabic)
- 📊 Score de similarité pour chaque résultat
- ⚡ Exemples cliquables pour tester rapidement
- 📱 Responsive (mobile-friendly)
- 🎯 Résultats avec catégories et prix

## 🚀 Comment utiliser

### 1. Démarrer le serveur API

```powershell
cd d:\template
.\.venv\Scripts\Activate.ps1
uvicorn app:app --reload --port 8001
```

### 2. Ouvrir l'interface

Allez sur: **http://localhost:8001/**

Ou directement: **http://localhost:8001/static/search.html**

### 3. Tester la recherche

**Exemples en anglais :**
- wireless headphones
- coffee maker
- laptop backpack
- smart watch

**Exemples en français :**
- machine espresso
- casque bluetooth
- sac à dos ordinateur

**Exemples en arabe :**
- سماعة بلوتوث
- حقيبة ظهر

## 📊 Affichage des résultats

Chaque produit affiche :
- **Nom** du produit
- **Score de similarité** (0-100%)
- **Catégorie**
- **Description**
- **Prix**
- **ID** du produit

## 🎨 Personnalisation

Pour modifier le design, éditez `static/search.html` :

- **Couleurs** : Modifiez les gradients CSS
- **Nombre de résultats** : Changez `limit=5` dans `app.py`
- **Exemples** : Ajoutez vos propres tags dans le HTML

## 🔧 API Endpoints utilisés

- `GET /search?q=...` - Recherche sémantique
- `GET /products` - Liste tous les produits

## 📱 Captures d'écran

Interface avec :
- Header gradient violet
- Barre de recherche élégante
- Tags d'exemples cliquables
- Cartes de produits avec hover effects
- Scores de similarité en badges

## 🛠️ Technologies

- HTML5 + CSS3 (Vanilla)
- JavaScript (Fetch API)
- FastAPI backend
- Responsive design
