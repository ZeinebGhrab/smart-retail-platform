# app/ — Agent RAG visiteurs ShopAnalytics

## En une phrase

Tu poses une question en français ("Combien de visiteurs hier ?"), et le
système te répond avec un **vrai chiffre** tiré du fichier Excel, ou avec
une **définition** tirée de la FAQ — selon le type de question.

```
Question (texte libre) → [LLM choisit un outil] → [Outil Python] → Réponse avec vrais chiffres
```

C'est un **agent AI simple** : un LLM (Llama 3.2 via Ollama) décide quel
outil utiliser parmi 4 possibilités, puis du code Python exécute cet outil
sur les vraies données. C'est le pattern "tool calling", la base de tous
les agents AI (Claude, ChatGPT + plugins, etc.) — mais ici en version
**single-step** (une seule décision, pas de boucle), **locale** (tout
tourne via Ollama, aucune donnée n'est envoyée à l'extérieur), et avec un
**filet de sécurité** (fallback par mots-clés).

---

## Les 3 fichiers, comme une équipe de 3 personnes

### `visitor_data.py` — le comptable

Il a le fichier `data/SA-data.xlsx` sous la main et sait faire 3 choses :

- **`get_visitor_count(date, camera)`** : "Combien de visiteurs ce jour-là ?"
  → lit la feuille `Per_Day`, renvoie le total + détail démographique
  (genre, âge).
- **`get_hourly_visitor_flow(date, camera)`** : "Comment était la
  fréquentation heure par heure ?" → lit la feuille `Per_Hour` (avec
  `ffill()` car Excel fusionne les cellules camera/date sur le premier
  bloc seulement).
- **`forecast_visitors(target_date, camera)`** : "Et demain, combien de
  visiteurs ?"
  - **Aujourd'hui** (1 seul jour de données dans `SA-data.xlsx`) : pas
    assez d'historique → répond honnêtement `model_status:
    "non_entraine"` et renvoie la dernière valeur connue à la place.
  - **Dès que ≥ 7 jours de données seront présents** : régression
    linéaire automatique (tendance + ajustement par jour de semaine),
    **sans changement de code**.

Toutes les fonctions normalisent les valeurs `"null"`/`"none"`/`""`
(parfois renvoyées par le LLM) en `None` pour éviter les erreurs
`pd.to_datetime`.

### `vector_store.py` — le bibliothécaire

Indexe `dataset/knowledge_base.json` (8 fiches FAQ : taux de conversion,
horaires du magasin, politique de confidentialité, etc.) dans une base
vectorielle **Chroma**, persistée sur disque (`vector_db/`).

- Utilise `DefaultEmbeddingFunction()` de Chroma — un petit modèle ONNX
  intégré, **sans torch/sentence-transformers/CUDA** (évite des
  téléchargements inutiles de plusieurs Go).
- **`reindex()`** : reconstruit l'index depuis zéro.
- **`semantic_search(query, n_results)`** : trouve les fiches les plus
  proches **par sens**, même si tu ne dis pas les mots exacts (ex.
  "panier moyen" trouvera la fiche sur le ticket moyen). Auto-reindex si
  la collection est vide.

### `visitor_agent.py` — le chef d'orchestre

C'est lui que tu appelles en premier (`answer_query`). Étapes :

```
question utilisateur
   │
   ▼
1. Prompt = TOOLS_SPEC + question
   │
   ▼
2. Appel Ollama /api/generate
   (modèle lu dans results/eligible_models.json)
   │
   ▼
3. Le LLM répond en JSON pur :
   {"tool": "...", "parameters": {...}}
   │
   ▼
4. parse_tool_call() extrait le JSON
   │
   ├─ JSON valide ──► _clean_params() ──► run_tool()
   │                  exécute la fonction Python correspondante
   │                  sur les vraies données (SA-data.xlsx / Chroma)
   │
   └─ JSON invalide / Ollama down ──► FALLBACK PAR MOTS-CLÉS :
        - "prévi/prédi/demain" → forecast_visitors
        - "horaire/flux/heure" → get_hourly_visitor_flow
        - "visiteur/visite"    → get_visitor_count
        - sinon                → search_knowledge_base
```

#### Les 4 outils exposés au LLM

| Outil                      | Quand l'utiliser                                  |
|-----------------------------|---------------------------------------------------|
| `get_visitor_count`          | "combien de visiteurs..."                          |
| `get_hourly_visitor_flow`     | "flux horaire...", "heure de pointe"               |
| `forecast_visitors`           | "prévision", "demain", "prédire"                   |
| `search_knowledge_base`        | questions générales/définitions (FAQ métier)        |

#### Pourquoi ce double niveau (LLM + fallback) ?

Le benchmark (section 7 du README principal) a mesuré que Llama 3.2 3B
produit du JSON valide **~94%** du temps — pas 100%. Le fallback par
mots-clés garantit qu'une **réponse pertinente sort toujours**, même si
le modèle local répond mal ou si Ollama est éteint. C'est une robustesse
"anti-hallucination" : on ne laisse jamais le système planter ou répondre
n'importe quoi.

---

## Pourquoi pas de RAG vectoriel sur `SA-data.xlsx` lui-même ?

- **Chiffres exacts** (2716 visiteurs, dates, heures) → recherche par
  **filtre/agrégat exact**, comme un Ctrl+F dans Excel. La recherche
  sémantique pourrait ramener des chiffres approximatifs ou faux.
- **Texte non structuré** (définitions, règles métier dans la FAQ) → la
  recherche **par sens** (vectorielle) a du sens : utile quand
  l'utilisateur ne formule pas la question avec les mots exacts.

C'est la différence entre chercher un numéro de téléphone précis
(annuaire = recherche exacte) et demander "qui pourrait m'aider avec un
problème de plomberie" (recherche par sens).

---

## Exemple de bout en bout

```
"Combien de visiteurs hier ?"
        │
        ▼
   LLM choisit l'outil → get_visitor_count(date=null)
        │
        ▼
   Lit SA-data.xlsx → 2716 visiteurs
        │
        ▼
   Réponse affichée à l'utilisateur

"C'est quoi le taux de conversion ?"
        │
        ▼
   LLM choisit l'outil → search_knowledge_base("taux de conversion")
        │
        ▼
   Trouve la fiche FAQ correspondante (recherche sémantique Chroma)
        │
        ▼
   Réponse affichée à l'utilisateur
```

---

## Et c'est quoi exactement comme "agent AI" ?

| Type                          | Exemple                                                        |
|-------------------------------|-----------------------------------------------------------------|
| Chatbot simple                 | Répond avec du texte généré, pas de données réelles              |
| **Ce projet**                   | LLM choisit un outil → exécute → données réelles (1 étape)        |
| Agent complexe (ReAct, AutoGPT) | Boucle multi-étapes, chaîne plusieurs outils, raisonne sur les résultats |

→ Un agent AI à **tool-calling simple, single-step, local (Ollama), avec
garde-fous** (fallback par mots-clés).

---

## Voir aussi

- `requirements.txt` : dépendances Python (pandas, chromadb, etc.)
- `../data/SA-data.xlsx` : source des données visiteurs (feuilles
  `Per_Day` / `Per_Hour`)
- `../dataset/knowledge_base.json` : les 8 fiches FAQ indexées par
  `vector_store.py`
- `../vector_db/` : index Chroma persisté (régénéré automatiquement si
  vide ou via `reindex()`)
- README principal, section 14 : commandes Docker/Makefile pour
  `reindex` et `ask`