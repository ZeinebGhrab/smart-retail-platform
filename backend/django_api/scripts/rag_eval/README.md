# Évaluation RAG — Anavid Store 360

Module d'évaluation du pipeline RAG (`history/rag_pipeline.py`) sur deux niveaux :
le **Retriever** (documents récupérés) et la **Génération** (réponse du LLM).

## Architecture du pipeline Anavid

```
Question utilisateur
       │
       ├──► _build_csv_context()   → données visiteurs (CSV) ──┐
       │                                                         ├──► _build_prompt() ──► Ollama (Llama 3.2)
       └──► _retrieve_kb()         → knowledge_base.json ───────┘
                (embeddings Ollama, cosine similarity)
```

Le Retriever a **deux sources** :
- **CSV** : données visiteurs structurées (`shoppingclub_2025_2026.csv`)
- **KB**  : 8 documents FAQ (`knowledge_base.json`), retrieval sémantique avec `n_results=2`

---

## Métriques implémentées

Cette section explique **ce que mesure chaque métrique, comment la lire, et pourquoi
elle compte** dans un système RAG. Les tableaux ci-dessous donnent la vue d'ensemble ;
les sous-sections détaillent chaque métrique avec un exemple concret tiré d'Anavid.

### 1. Retriever (`metrics_retriever.py`)

Le Retriever est la première étape du pipeline : avant même que le LLM écrive un mot,
le système doit retrouver les **bons documents** (KB) et/ou les **bonnes données**
(CSV). Si cette étape échoue, le LLM ne peut pas bien répondre, même s'il est
excellent — c'est pour ça qu'on évalue le Retriever séparément de la Génération.

| Métrique | Formule | Adapté à Anavid |
|---|---|---|
| **Precision@K** | docs pertinents récupérés / K | K=2 (n_results du pipeline) |
| **Recall@K** | docs pertinents récupérés / docs pertinents existants | Sur les 8 docs KB |
| **MRR** | 1 / rang du premier doc pertinent | Position dans le ranking cosine |
| **nDCG@K** | DCG / IDCG, pondéré par position | Qualité du classement sémantique |
| **Context Precision** | passages KB utiles dans la réponse / total récupérés | Réduit le bruit envoyé au LLM |
| **Context Recall** | couverture des infos nécessaires par le contexte | CSV + KB couvrent la ground truth ? |

#### Precision@K — "Parmi ce qu'on a récupéré, combien est pertinent ?"

Mesure la proportion de documents **utiles** parmi les K documents renvoyés par
`_retrieve_kb()`. Une Precision@2 de 0.50 veut dire qu'1 document sur 2 récupérés
est réellement pertinent pour la question — l'autre n'est que du bruit ajouté au
prompt.

- **Rôle dans le RAG** : une Precision@K basse signifie que le LLM reçoit des
  passages hors-sujet en plus du bon contexte. Ce bruit peut le distraire ou
  diluer l'information utile dans le prompt.
- **Interprétation** : 1.0 = tous les documents récupérés sont pertinents.
  0.0 = aucun document pertinent dans le top-K (le retrieval a complètement raté).

#### Recall@K — "Parmi tout ce qui est pertinent, combien a-t-on retrouvé ?"

Mesure la proportion de documents pertinents qui ont **effectivement été
récupérés**, sur l'ensemble des documents pertinents qui existent dans la KB.

- **Rôle dans le RAG** : un Recall@K bas signifie que des informations utiles
  existent dans la base de connaissances mais ne sont jamais montrées au LLM —
  un problème souvent plus grave qu'une Precision basse, car aucune réponse
  ne peut compenser une information totalement absente du contexte.
- **Interprétation** : 1.0 = tous les documents pertinents ont été trouvés.

#### MRR (Mean Reciprocal Rank) — "Le bon document apparaît-il en premier ?"

Calcule l'inverse du rang du premier document pertinent (1/rang), moyenné sur
toutes les requêtes. Si le bon document est en position 1 → score 1.0 ; en
position 2 → 0.5 ; etc.

- **Rôle dans le RAG** : avec la règle système *"base-toi sur le premier document
  uniquement"* du prompt Anavid, le MRR est particulièrement important — si le bon
  document KB n'est pas en première position, le LLM risque de l'ignorer.
- **Interprétation** : proche de 1.0 = le bon document arrive presque toujours
  en tête du classement.

#### nDCG@K (Normalized Discounted Cumulative Gain) — "La qualité du classement"

Comme le MRR, mais plus nuancé : il récompense un bon classement même quand il y
a plusieurs documents pertinents, en pondérant chaque position (un document
pertinent en position 1 compte plus qu'en position 2).

- **Rôle dans le RAG** : utile quand une question peut légitimement matcher
  plusieurs documents KB — il vérifie que les meilleurs sont bien classés en tête.
- **Interprétation** : 1.0 = classement parfait (les documents les plus
  pertinents sont en tête, dans le bon ordre).

#### Context Precision — "Le contexte récupéré est-il utilisé ?"

Spécifique aux systèmes RAG (contrairement aux 4 métriques précédentes, issues
de la recherche d'information classique). Vérifie si les **mots-clés** de chaque
passage récupéré apparaissent réellement dans la réponse générée — un signe que
ce passage a servi, et non qu'il a juste ajouté du bruit.

- **Rôle dans le RAG** : détecte le sur-retrieval (récupérer trop de documents
  "au cas où", dont la plupart ne servent jamais).
- **Interprétation** : 1.0 = chaque passage récupéré a laissé une trace dans
  la réponse. Score bas = beaucoup de contexte inutilisé.

#### Context Recall — "Le contexte suffit-il pour bien répondre ?"

Vérifie si les passages récupérés (CSV + KB combinés) contiennent bien tous les
mots-clés significatifs présents dans la réponse de référence (`ground_truth`).

- **Rôle dans le RAG** : un Context Recall bas est souvent la cause racine d'un
  Answer Relevancy ou Faithfulness bas en aval — si l'info nécessaire n'est pas
  dans le contexte, le LLM ne peut objectivement pas bien répondre.
- **Interprétation** : 1.0 = le contexte contient toute l'info nécessaire pour
  formuler la réponse attendue.

### 2. Génération (`metrics_generation.py`)

Une fois le contexte récupéré, ces métriques évaluent la **réponse rédigée par
le LLM** (Llama 3.2 3B). Elles répondent à deux questions différentes : *"la
réponse ressemble-t-elle à ce qu'on attendait ?"* (EM, F1, BLEU, ROUGE-L) et
*"la réponse est-elle fiable et pertinente, indépendamment de sa formulation
exacte ?"* (Faithfulness, Answer Relevancy).

| Métrique | Usage dans Anavid |
|---|---|
| **Exact Match** | Rarement 1.0 (réponses libres en français) — indicatif |
| **F1 Score** | Chevauchement tokens prédit/attendu — principal indicateur qualité texte |
| **BLEU-2** | N-grammes bigrammes — cohérence locale |
| **ROUGE-L** | Sous-séquence commune — ordre préservé |
| **Faithfulness** | ⭐ Priorité #1 — le LLM n'invente pas de chiffres hors contexte |
| **Answer Relevancy** | La réponse cible bien la question posée |

#### Exact Match (EM) — "La réponse est-elle identique mot pour mot ?"

Vaut 1.0 si la réponse générée correspond exactement à la `ground_truth` (après
normalisation : minuscules, ponctuation retirée), 0.0 sinon.

- **Rôle dans le RAG** : très strict — peu adapté à un chatbot qui rédige des
  phrases libres en français. Sert surtout de signal extrême ("la réponse est
  formulée EXACTEMENT comme prévu"), pas de métrique principale.
- **Interprétation** : à peu près toujours 0.0 dans ce projet — c'est normal,
  ce n'est pas la métrique à surveiller.

#### F1 Score — "Combien de mots corrects, en ignorant l'ordre ?"

Standard en question-réponse (benchmark SQuAD). Compare les tokens de la
réponse générée à ceux de la `ground_truth` : Précision = part des mots de la
réponse qui sont corrects, Recall = part des mots attendus qui sont présents,
F1 = moyenne harmonique des deux.

- **Rôle dans le RAG** : donne une mesure de qualité textuelle plus tolérante
  que l'Exact Match (l'ordre des mots ne compte pas), tout en restant exigeante
  sur le contenu.
- **Interprétation** : 1.0 = même contenu lexical exact. 0.0 = aucun mot en
  commun. Dans ce projet, un F1 entre 0.4 et 0.7 est courant pour une réponse
  correcte mais formulée différemment de la référence.

#### ROUGE-L — "La réponse suit-elle le même fil que l'attendu ?"

Basé sur la plus longue sous-séquence commune (LCS) entre la réponse et la
`ground_truth` — contrairement au F1, **l'ordre des mots compte**.

- **Rôle dans le RAG** : pertinent pour des réponses qui doivent suivre une
  structure logique (ex : énumérer une procédure dans l'ordre), ce qui est
  fréquent dans les réponses KB d'Anavid (horaires, procédures, définitions).
- **Interprétation** : 1.0 = même séquence de mots dans le même ordre. Un score
  ROUGE-L plus bas que le F1 sur une même réponse indique que le bon contenu est
  présent mais reformulé dans un ordre différent.

#### BLEU-2 — "Les groupes de 2 mots se retrouvent-ils ?"

Mesure le chevauchement de bigrammes (paires de mots consécutifs) entre la
réponse et la référence, avec une pénalité si la réponse est trop courte.

- **Rôle dans le RAG** : capture la cohérence locale (les bonnes expressions au
  bon endroit), mais reste **secondaire** dans ce projet — le README du module
  le précise déjà : *"BLEU a des limitations sur des phrases courtes (variance
  élevée). Préférer F1 et ROUGE-L."*
- **Interprétation** : à regarder en complément du F1/ROUGE-L, pas isolément.

#### Faithfulness — "Le LLM invente-t-il des choses ?" ⭐ Priorité #1

La métrique la plus importante du projet. Elle vérifie que **chaque chiffre et
chaque mot-clé substantiel de la réponse provient bien du contexte fourni**
(CSV + KB) — et non de la mémoire générale du modèle ou d'une invention.

- **Rôle dans le RAG** : c'est la métrique anti-hallucination. Le prompt système
  d'Anavid impose *"Utilise UNIQUEMENT les chiffres et faits présents dans le
  CONTEXTE"* — Faithfulness vérifie que cette règle est vraiment respectée.
- **Interprétation** : 1.0 = chaque chiffre/fait mentionné est vérifiable dans
  le contexte envoyé au LLM (zéro hallucination détectée). Une Faithfulness
  basse est un signal d'alerte sérieux : le LLM répond à côté du contexte fourni.
- **Pourquoi elle pèse 30 pts sur 100 dans le score global** : dans un outil
  d'aide à la décision retail, une statistique inventée (ex : un nombre de
  visiteurs faux) est largement plus dangereuse qu'une réponse incomplète ou
  mal formulée — d'où la priorité absolue donnée à cette métrique.

#### Answer Relevancy — "La réponse cible-t-elle vraiment la question ?"

Vérifie si les mots-clés de la **question** posée se retrouvent dans la
**réponse** générée — une réponse peut être 100% fidèle au contexte (aucune
hallucination) tout en étant hors-sujet par rapport à ce qui était demandé.

- **Rôle dans le RAG** : complète Faithfulness. Une réponse du type "📈 1639"
  peut être parfaitement fidèle au contexte (le chiffre est correct) mais avoir
  un Answer Relevancy proche de 0, car elle ne reformule ni la date, ni la
  caméra demandée, ni le mot "visiteurs" — l'utilisateur ne peut même pas
  vérifier de quoi parle la réponse sans relire sa propre question.
- **Interprétation** : 1.0 = tous les mots-clés importants de la question
  apparaissent dans la réponse. Score bas = réponse correcte sur le fond, mais
  qui "perd le fil" de ce qui était précisément demandé.

### 3. Score global (/100)

| Composante | Poids | Seuil recommandé |
|---|---|---|
| Faithfulness | 30 pts | ≥ 0.70 |
| Answer Relevancy | 20 pts | ≥ 0.60 |
| Context Recall | 15 pts | ≥ 0.60 |
| F1 Score | 15 pts | ≥ 0.50 |
| Precision@K | 10 pts | ≥ 0.75 |
| MRR | 10 pts | ≥ 0.75 |

La pondération reflète les priorités du projet Anavid : la fiabilité
(Faithfulness) et la pertinence (Answer Relevancy) comptent pour la moitié du
score, car un chatbot retail qui se trompe sur des chiffres ou qui répond à
côté perd la confiance des utilisateurs bien plus vite qu'un chatbot dont la
formulation est juste un peu différente de l'idéal.

---

## Paramètres de génération (Ollama)

Le pipeline Anavid appelle Llama 3.2 3B via Ollama (`/api/generate`) avec des
paramètres explicites à chaque étape. Cette section explique ce que fait
chacun, et pourquoi leurs valeurs ont été choisies ainsi pour ce projet.

### Temperature — créativité vs fiabilité

La `temperature` contrôle le degré d'aléatoire dans le choix du mot suivant
généré par le LLM.

- **Température haute (ex: 0.7–1.0)** : le modèle explore des formulations plus
  variées et créatives, mais devient aussi plus susceptible d'inventer des
  détails absents du contexte (hallucinations) — utile pour de la rédaction
  créative, risqué pour un assistant analytique qui doit rapporter des chiffres
  exacts.
- **Température basse (ex: 0.0–0.3)** : le modèle privilégie systématiquement
  les mots les plus probables compte tenu du contexte, ce qui le rend plus
  prévisible, plus factuel, et plus fidèle aux données fournies.

**Dans Anavid** :
| Appel | Temperature | Pourquoi |
|---|---|---|
| Génération de la réponse finale | `0.0` | Réponses déterministes et factuelles — priorité à la fidélité au contexte (Faithfulness) sur la créativité |
| Classification d'intention (FUTUR/PASSE) | `0.0` | Une seule réponse possible attendue (un mot) — aucune place pour la variation |
| Retry anti-troncature | `0.2` | Légèrement augmentée pour donner au modèle une vraie chance de reformuler différemment plutôt que de répéter la même réponse tronquée |

### Seed — reproductibilité

La `seed` fixe le point de départ du générateur pseudo-aléatoire utilisé par
le modèle. Avec une seed fixe et `temperature=0.0`, deux appels avec
**exactement le même prompt** produisent (en théorie) **exactement la même
réponse**.

- **Pourquoi c'est important pour ce projet** :
  - **Reproductibilité des tests** : relancer `evaluate_rag.py` plusieurs fois
    sur le même dataset doit donner des résultats comparables, sinon il devient
    impossible de savoir si un changement de score vient d'une vraie
    amélioration du pipeline ou simplement du hasard de génération.
  - **Débogage** : face à une réponse incorrecte, pouvoir la reproduire à
    l'identique est indispensable pour identifier la cause (mauvais contexte ?
    mauvaise règle système ? comportement du modèle ?).
  - **Limite à connaître** : la seed garantit la reproductibilité *pour un
    prompt identique*. Si le contexte change (nouvelles données CSV, nouvelle
    KB), la réponse changera aussi — c'est attendu et normal.

**Dans Anavid** : `seed=42` pour la génération principale, `seed=0` pour la
classification d'intention, `seed=43` pour le retry (volontairement différente
de 42, car réutiliser la même seed sur le même prompt régénérerait
exactement la même réponse tronquée plutôt que d'en produire une nouvelle).

### Top-p (nucleus sampling)

Le `top_p` restreint le choix du mot suivant aux mots dont la probabilité
cumulée atteint ce seuil (ex : `top_p=0.9` ne considère que les mots les plus
probables jusqu'à couvrir 90% de la masse de probabilité), en ignorant la
longue traîne de mots peu probables.

- **Rôle** : agit en complément de la température. Une température basse limite
  déjà beaucoup la variation ; le `top_p=0.9` utilisé dans Anavid sert surtout
  de garde-fou supplémentaire pour éviter qu'un mot très improbable ne soit
  choisi par accident.
- **Dans Anavid** : `top_p=0.9` sur tous les appels de génération de réponse.

### Pourquoi cette configuration compte pour Anavid

1. **Stabilité des résultats** : avec `temperature=0.0`, deux questions
   similaires posées à des moments différents reçoivent un traitement cohérent
   — important pour un outil utilisé en continu par des équipes retail.
2. **Reproductibilité des tests** : `seed` fixe + `temperature` basse permettent
   de comparer deux versions du pipeline (avant/après un changement de prompt
   ou de code) sur une base équitable, comme observé au fil des itérations
   d'évaluation de ce projet — sans cette stabilité, impossible de savoir si
   un score qui change vient d'un vrai progrès ou du hasard.
3. **Réduction des hallucinations** : une température basse réduit la tendance
   du modèle à "broder" au-delà du contexte fourni, ce qui se traduit
   directement par une meilleure Faithfulness — la métrique la plus pondérée
   du score global (30/100).
4. **Fiabilité de l'évaluation RAG** : `evaluate_rag.py` mesure la qualité du
   pipeline ; si la génération elle-même était trop aléatoire, les métriques
   varieraient d'un run à l'autre sans rapport avec une vraie amélioration ou
   régression du code — la configuration basse-température/seed-fixe est ce
   qui rend les comparaisons de scores entre deux runs réellement informatives.

### Configuration recommandée

Pour ce projet (assistant analytique factuel, pas créatif), la plage
recommandée pour un nouveau projet RAG similaire est la suivante. Le pipeline
Anavid utilise actuellement `temperature=0.0` (le bas de cette plage) pour
la génération principale, ce qui reste cohérent avec la recommandation :

```python
options = {
    "temperature": 0.1,   # plage recommandée : 0.0–0.3 (Anavid utilise 0.0)
    "top_p":       0.9,
    "seed":        42,    # toute valeur fixe convient — l'important est qu'elle ne change pas entre deux runs comparés
    "num_ctx":     4096,
    "num_predict": 2048,
}
```

- **`temperature` entre 0.1 et 0.3** : assez basse pour rester factuel et
  fidèle au contexte, tout en laissant une marge minimale pour éviter des
  réponses trop mécaniques ou répétitives sur des questions très proches.
- **`seed` fixe (ex: 42)** : n'importe quelle valeur convient, à condition de
  rester identique entre deux évaluations qu'on veut comparer.
- À éviter pour ce cas d'usage : `temperature > 0.5`, qui augmente le risque
  de réponses créatives mais non fondées sur le contexte (donc une
  Faithfulness plus basse).

---

## Usage

```bash
# Depuis backend/scripts/
cd backend/scripts

# Mode réel (Ollama doit tourner)
python rag_eval/evaluate_rag.py

# Mode dry-run (sans Ollama — test du module)
python rag_eval/evaluate_rag.py --dry-run

# Verbose (détail par requête)
python rag_eval/evaluate_rag.py --verbose

# Dataset personnalisé
python rag_eval/evaluate_rag.py --dataset /chemin/mon_dataset.json
```

### Via Docker Compose

```bash
# Ajouter au Makefile ou lancer manuellement
docker compose exec django_api python /app/scripts/rag_eval/evaluate_rag.py
```

---

## Structure des fichiers

```
backend/scripts/rag_eval/
├── __init__.py
├── eval_dataset.json          # 12 requêtes avec ground truth
├── metrics_retriever.py       # Precision@K, Recall@K, MRR, nDCG, Context P/R
├── metrics_generation.py      # EM, F1, BLEU, ROUGE-L, Faithfulness, Relevancy
└── evaluate_rag.py            # Runner principal + rapport JSON

backend/results/
└── rag_eval_report.json       # Rapport généré après évaluation
```

---

## Format du dataset d'évaluation

```json
[
  {
    "id": "eval-001",
    "question": "Quels sont les horaires d'ouverture du magasin ?",
    "ground_truth": "Le magasin est ouvert du lundi au samedi de 9h à 20h...",
    "relevant_kb_ids": ["kb-001"],
    "relevant_source": "kb",       // "kb" | "csv" | "both"
    "category": "faq"              // "faq" | "data" | "hybrid"
  }
]
```

---

## Interprétation des résultats

### Faithfulness faible (< 0.70)
Le LLM génère des chiffres ou faits absents du contexte. Actions :
- Renforcer le prompt système : *"Ne génère AUCUN chiffre absent du contexte"*
- Réduire `temperature` (déjà à 0.0 pour la génération principale — voir [Paramètres de génération](#paramètres-de-génération-ollama) ; si le problème persiste, vérifier plutôt le contenu du CONTEXTE lui-même)
- Vérifier que `_build_csv_context()` renvoie des données pour la date demandée

### Precision@K faible (< 0.75)
La recherche sémantique KB ramène des documents non pertinents. Actions :
- Augmenter le seuil de similarité cosine dans `_retrieve_kb()`
- Enrichir les titres/contenus KB pour améliorer les embeddings

### Context Recall faible (< 0.60)
Le contexte fourni ne contient pas toutes les infos pour répondre. Actions :
- Augmenter `n_results` de 2 à 3 dans `_retrieve_kb()`
- Enrichir `_build_csv_context()` pour des questions hybrides

### Answer Relevancy faible (< 0.60)
Les réponses sont correctes mais ne ciblent pas la question. Actions :
- Ajouter dans le prompt : *"Réponds directement et précisément à la question"*
- Vérifier les cas `"résumé"` dans `_build_csv_context()` qui génère un contexte global

---

## Évolution : RAGAS en production

Ce module utilise une évaluation **lexicale offline** (sans LLM-as-judge) pour rester
cohérent avec l'architecture Anavid (100% local, Ollama, pas d'API externe).

Pour passer à une évaluation basée sur un LLM-juge (RAGAS) :

```python
# Installer : pip install ragas
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall

result = evaluate(
    dataset=dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
)
```

RAGAS nécessite un LLM juge (OpenAI par défaut, ou Ollama avec adaptation).