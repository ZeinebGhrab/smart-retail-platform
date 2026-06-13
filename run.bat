@echo off
REM ============================================================
REM run.bat — ShopAnalytics LLM Benchmark (Windows)
REM Usage : run.bat [commande]
REM   run.bat           → Lance tout : frontend + backend complet
REM   run.bat dev       → Lance tout : frontend + Ollama (sans benchmark)
REM   run.bat up        → Lance Ollama + benchmark complet (sans frontend)
REM   run.bat ollama    → Lance uniquement Ollama
REM   run.bat bench     → Lance uniquement le benchmark
REM   run.bat frontend  → Lance uniquement le frontend
REM   run.bat reindex   → (Re)construit la base vectorielle (FAQ)
REM   run.bat ask "..." → Pose une question a l'agent RAG
REM   run.bat logs      → Logs Ollama en live
REM   run.bat status    → Statut des containers
REM   run.bat down      → Arrete tout
REM   run.bat clean     → Supprime les resultats JSON
REM   run.bat clean-all → Supprime tout (volumes inclus)
REM ============================================================

SET CMD=%1
IF "%CMD%"=="" SET CMD=all

IF "%CMD%"=="all"      GOTO ALL
IF "%CMD%"=="dev"      GOTO DEV
IF "%CMD%"=="up"       GOTO UP
IF "%CMD%"=="ollama"   GOTO OLLAMA
IF "%CMD%"=="bench"    GOTO BENCH
IF "%CMD%"=="frontend" GOTO FRONTEND
IF "%CMD%"=="reindex"  GOTO REINDEX
IF "%CMD%"=="ask"      GOTO ASK
IF "%CMD%"=="logs"     GOTO LOGS
IF "%CMD%"=="status"   GOTO STATUS
IF "%CMD%"=="down"     GOTO DOWN
IF "%CMD%"=="clean"    GOTO CLEAN
IF "%CMD%"=="clean-all" GOTO CLEAN_ALL

echo [ERREUR] Commande inconnue : %CMD%
echo Usage : run.bat [all^|dev^|up^|ollama^|bench^|frontend^|reindex^|ask^|logs^|status^|down^|clean^|clean-all]
EXIT /B 1

REM ── ALL : frontend + Ollama + benchmark ─────────────────────
:ALL
echo ==============================================
echo  ShopAnalytics — Demarrage complet
echo  Frontend  : http://localhost:5173
echo  Ollama    : http://localhost:11434
echo ==============================================

REM 1) Ollama en arriere-plan
docker compose up -d ollama
IF ERRORLEVEL 1 (echo [ERREUR] Impossible de demarrer Ollama. & EXIT /B 1)

REM 2) Frontend en arriere-plan
docker compose up -d frontend
IF ERRORLEVEL 1 (echo [ERREUR] Impossible de demarrer le frontend. & EXIT /B 1)

REM 3) Attente Ollama
echo Attente Ollama pret...
:WAIT_ALL
curl -sf http://localhost:11434/api/tags >NUL 2>&1
IF ERRORLEVEL 1 (
    timeout /t 2 /nobreak >NUL
    GOTO WAIT_ALL
)
echo Ollama pret !

REM 4) Benchmark one-shot
docker compose run --rm benchmark

echo.
echo ==============================================
echo  Tout est demarre !
echo  Frontend  : http://localhost:5173
echo  Ollama    : http://localhost:11434
echo  run.bat logs    pour voir les logs
echo  run.bat status  pour l'etat des containers
echo  run.bat down    pour tout arreter
echo ==============================================
GOTO END

REM ── DEV : frontend + Ollama (sans benchmark) ────────────────
:DEV
echo ==============================================
echo  ShopAnalytics — Mode dev
echo  Frontend  : http://localhost:5173
echo  Ollama    : http://localhost:11434
echo ==============================================

docker compose up -d ollama
IF ERRORLEVEL 1 (echo [ERREUR] Impossible de demarrer Ollama. & EXIT /B 1)

docker compose up -d frontend
IF ERRORLEVEL 1 (echo [ERREUR] Impossible de demarrer le frontend. & EXIT /B 1)

echo.
echo Attente Ollama pret...
:WAIT_DEV
curl -sf http://localhost:11434/api/tags >NUL 2>&1
IF ERRORLEVEL 1 (
    timeout /t 2 /nobreak >NUL
    GOTO WAIT_DEV
)
echo Ollama pret !

echo.
echo ==============================================
echo  Mode dev demarre !
echo  Frontend  : http://localhost:5173
echo  Ollama    : http://localhost:11434
echo  run.bat bench   pour lancer le benchmark
echo  run.bat down    pour tout arreter
echo ==============================================
GOTO END

REM ── UP : Ollama + benchmark (sans frontend) ─────────────────
:UP
echo Demarrage Ollama + benchmark...
docker compose up -d ollama
IF ERRORLEVEL 1 (echo [ERREUR] Impossible de demarrer Ollama. & EXIT /B 1)

echo Attente Ollama pret...
:WAIT_UP
curl -sf http://localhost:11434/api/tags >NUL 2>&1
IF ERRORLEVEL 1 (
    timeout /t 2 /nobreak >NUL
    GOTO WAIT_UP
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

:FRONTEND
echo Demarrage du frontend (http://localhost:5173)...
docker compose up frontend
GOTO END

:REINDEX
echo (Re)construction de la base vectorielle...
docker compose run --rm agent bash -c "python vector_store.py --reindex"
GOTO END

:ASK
SET Q=%~2
IF "%Q%"=="" (
    echo [ERREUR] Fournir une question : run.bat ask "Combien de visiteurs hier ?"
    EXIT /B 1
)
echo Question : %Q%
docker compose run --rm agent bash -c "python visitor_agent.py \"%Q%\""
GOTO END

:LOGS
docker compose logs -f ollama
GOTO END

:STATUS
docker compose ps
GOTO END

:DOWN
echo Arret de tous les containers...
docker compose down
echo Arrete.
GOTO END

:CLEAN
echo Suppression des resultats benchmark...
IF EXIST backend\results\*.json del /Q backend\results\*.json
echo Fait.
GOTO END

:CLEAN_ALL
echo Suppression complete (volumes inclus)...
docker compose down -v
IF EXIST backend\results\*.json del /Q backend\results\*.json
echo Fait.
GOTO END

:END