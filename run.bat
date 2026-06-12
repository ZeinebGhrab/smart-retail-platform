@echo off
REM ============================================================
REM run.bat — ShopAnalytics LLM Benchmark (Windows)
REM Usage : run.bat [commande]
REM   run.bat up          → Lance Ollama + benchmark complet
REM   run.bat ollama      → Lance uniquement Ollama
REM   run.bat bench       → Lance uniquement le benchmark
REM   run.bat logs        → Logs Ollama en live
REM   run.bat status      → Statut des containers
REM   run.bat down        → Arrête tout
REM   run.bat clean       → Supprime les résultats JSON
REM   run.bat reindex     → (Re)construit la base vectorielle (FAQ)
REM   run.bat ask "..."   → Pose une question à l'agent RAG (visiteurs + FAQ)
REM ============================================================

SET CMD=%1
IF "%CMD%"=="" SET CMD=up

IF "%CMD%"=="up" GOTO UP
IF "%CMD%"=="ollama" GOTO OLLAMA
IF "%CMD%"=="bench" GOTO BENCH
IF "%CMD%"=="logs" GOTO LOGS
IF "%CMD%"=="status" GOTO STATUS
IF "%CMD%"=="down" GOTO DOWN
IF "%CMD%"=="clean" GOTO CLEAN
IF "%CMD%"=="reindex" GOTO REINDEX
IF "%CMD%"=="ask" GOTO ASK

echo [ERREUR] Commande inconnue : %CMD%
echo Usage : run.bat [up^|ollama^|bench^|logs^|status^|down^|clean^|reindex^|ask]
EXIT /B 1

:UP
echo ==============================================
echo  ShopAnalytics — Demarrage complet
echo ==============================================
docker compose up -d ollama
IF ERRORLEVEL 1 (echo [ERREUR] Impossible de demarrer Ollama. & EXIT /B 1)

echo Attente Ollama pret...
REM NOTE : l'image ollama/ollama ne contient pas curl, donc on teste
REM depuis l'hote (curl.exe est natif sur Windows 10/11) via le port expose.
:WAIT_LOOP
curl -sf http://localhost:11434/api/tags >NUL 2>&1
IF ERRORLEVEL 1 (
    timeout /t 2 /nobreak >NUL
    GOTO WAIT_LOOP
)
echo Ollama pret !

docker compose run --rm benchmark
GOTO END

:OLLAMA
echo Demarrage Ollama uniquement...
docker compose up -d ollama
GOTO END

:BENCH
echo Lancement du benchmark (Ollama doit deja tourner)...
docker compose run --rm benchmark
GOTO END

:LOGS
docker compose logs -f ollama
GOTO END

:STATUS
docker compose ps
GOTO END

:DOWN
docker compose down
GOTO END

:CLEAN
echo Suppression des resultats...
IF EXIST results\*.json del /Q results\*.json
echo Fait.
GOTO END

:REINDEX
echo (Re)construction de la base vectorielle (FAQ)...
docker compose run --rm agent bash -c "pip install -q -r requirements.txt && python vector_store.py --reindex"
GOTO END

:ASK
SET Q=%~2
echo Question : %Q%
docker compose run --rm agent bash -c "pip install -q -r requirements.txt && python visitor_agent.py \"%Q%\""
GOTO END

:END