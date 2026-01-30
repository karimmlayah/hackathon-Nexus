# Comment tester les recommandations (Pour vous)

Les recommandations **changent par compte** selon ce que vous **cherchez**, mettez en **favoris** et **panier**. Tout est enregistré en SQLite (`rag_app.db`).

---

## 1. Vérifier que le backend utilise bien SQLite

Dans le navigateur ou avec curl :

```
GET http://127.0.0.1:8000/api/recommendations/debug?user_email=VOTRE_EMAIL
```

Exemple : si vous êtes connecté avec `test@example.com` :

- **Navigateur :**  
  http://127.0.0.1:8000/api/recommendations/debug?user_email=test@example.com

- **Réponse attendue :**
  - `sqlite_interactions_count` : nombre d’interactions en base pour ce compte
  - `product_ids_from_sqlite` : IDs produits (favoris, panier, vues)
  - `search_queries_from_sqlite` : dernières recherches
  - `strategy_will_be` : `"by-seed (SQLite)"` si des données existent, sinon `"fallback (Qdrant/trending)"`

Si `sqlite_interactions_count` est 0, les recommandations viennent du fallback (liste plus générique). Dès que vous avez des recherches / favoris / panier enregistrés, elles passent en **by-seed (SQLite)**.

---

## 2. Scénario de test (recommandations qui changent)

1. **Démarrer l’app**  
   `uvicorn app:app --reload`

2. **Se connecter**  
   Aller sur Sign in, se connecter avec un compte (ou s’inscrire).

3. **Faire une recherche**  
   Barre de recherche : taper un mot (ex. "phone", "cable") et lancer la recherche.  
   → Une interaction **search** est enregistrée en base.

4. **Ajouter aux favoris**  
   Sur un produit, cliquer sur le cœur.  
   → Une interaction **wishlist** est enregistrée.

5. **Ajouter au panier**  
   Sur un produit, cliquer sur "Add to Cart".  
   → Une interaction **add_to_cart** est enregistrée.

6. **Ouvrir « Pour vous »**  
   Cliquer sur l’onglet **Pour vous** (coeur).  
   → La page recharge les recommandations (sans cache, avec `_t=...`).  
   → Si le backend a trouvé des données en SQLite pour votre compte, vous devez voir :
     - Un sous-titre du type : **« Recommandations basées sur vos recherches, favoris et panier »**
     - Des produits **similaires** à ce que vous avez cherché / mis en favoris / en panier.

7. **Re-vérifier avec le debug**  
   Ouvrir :  
   `http://127.0.0.1:8000/api/recommendations/debug?user_email=VOTRE_EMAIL`  
   Vous devez voir `sqlite_interactions_count` > 0 et `strategy_will_be` = `"by-seed (SQLite)"`.

---

## 3. Vérifier les données en base (SQLite)

```bash
sqlite3 rag_app.db "SELECT interaction_type, COUNT(*) FROM user_interactions GROUP BY interaction_type;"
```

Pour un utilisateur précis (remplacer `USER_ID` par l’id du user dans `auth_user`) :

```bash
sqlite3 rag_app.db "SELECT id, interaction_type, product_id, created_at FROM user_interactions WHERE user_id = USER_ID ORDER BY created_at DESC LIMIT 20;"
```

---

## 4. Si les recommandations restent « fixes »

- Vérifier que vous êtes **bien connecté** (même email que celui passé dans `user_email`).
- Appeler le **debug** avec cet email : les compteurs et `strategy_will_be` confirment si SQLite est utilisé.
- Vérifier que des **interactions** existent pour ce user : recherche, favoris, panier au moins une fois.
- Recliquer sur **Pour vous** pour forcer un nouvel appel API (pas de cache côté front).
