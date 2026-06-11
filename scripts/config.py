# ============================================================
# config.py — ShopAnalytics LLM Benchmark Configuration
# ============================================================

# Ollama host (override via env OLLAMA_HOST)
OLLAMA_HOST = "http://ollama:11434"

# ── Modèles candidats ────────────────────────────────────────
# Format Ollama : "nom:tag"
# q4_K_M = quantification 4 bits, meilleur équilibre vitesse/qualité
CANDIDATE_MODELS = [
    {
        "id": "qwen2.5:7b-instruct-q4_K_M",
        "label": "Qwen 2.5 7B (q4_K_M)",
        "params_b": 7,
        "notes": "Meilleur FR/AR sur 6Go, tool calling solide",
    },
    {
        "id": "mistral:7b-instruct-v0.3-q4_K_M",
        "label": "Mistral 7B Instruct v0.3 (q4_K_M)",
        "params_b": 7,
        "notes": "Rapide, bon JSON",
    },
    {
        "id": "llama3.2:3b-instruct-q4_K_M",
        "label": "Llama 3.2 3B (q4_K_M)",
        "params_b": 3,
        "notes": "Très léger, baseline de vitesse",
    },
]

# ── Seuils de performance (depuis rapport 11/06) ─────────────
THRESHOLDS = {
    "ttft_max_sec": 1.5,          # Temps jusqu'au premier token (s)
    "throughput_min_tps": 20.0,   # tokens/s idéal
    "throughput_hard_min": 10.0,  # tokens/s minimum absolu
    "json_success_min_pct": 95.0, # % de réponses JSON valides (tool calling)
}

# ── Filtrage matériel ────────────────────────────────────────
# VRAM requise ≈ params_b × 0.7 + 2 Go (règle empirique q4_K_M)
VRAM_AVAILABLE_GB = 5.5  # Mettre à jour selon le serveur cible

def vram_required_gb(params_b: float) -> float:
    return params_b * 0.7 + 2.0

# ── Paramètres d'inférence ───────────────────────────────────
INFERENCE_OPTIONS = {
    "temperature": 0.1,    # faible = plus déterministe pour tool calling
    "top_p": 0.9,
    "num_ctx": 4096,       # contexte de test (augmenter pour test de latency penalty)
    "num_predict": 256,    # tokens max générés par requête
}

# Nombre de répétitions par test pour moyenner les résultats
N_WARMUP = 1    # requêtes ignorées (JIT/cache warmup)
N_RUNS = 3      # requêtes mesurées

# Fichiers de sortie
RESULTS_DIR = "/workspace/results"
DATASET_PATH = "/workspace/dataset/tool_calling_queries.json"
