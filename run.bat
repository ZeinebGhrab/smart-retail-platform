@echo off
REM ============================================================
REM run.bat — ShopAnalytics (Windows)
REM Usage : run.bat [commande]
REM   run.bat           → Lance tout : Ollama + benchmark + API + Frontend
REM   run.bat ollama    → Lance uniquement Ollama
REM   run.bat bench     → Lance uniquement le benchmark
REM   run.bat django    → Lance uniquement l'API Django (http://localhost:8000)
REM   run.bat api       → Lance Django + Frontend (sans Ollama)
REM   run.bat frontend  → Lance uniquement le frontend
REM   run.bat logs      → Logs Ollama en live
REM   run.bat status    → Statut des containers
REM   run.bat down      → Arrete tout
REM   run.bat clean     → Supprime les resultats JSON
REM   run.bat clean-all → Supprime tout (volumes inclus)
REM ============================================================

SET CMD=%1
IF "%CMD%"=="" SET CMD=all

IF "%CMD%"=="all"      GOTO ALL
IF "%CMD%"=="ollama"   GOTO OLLAMA
IF "%CMD%"=="bench"    GOTO BENCH
IF "%CMD%"=="django"   GOTO DJANGO
IF "%CMD%"=="api"      GOTO API
IF "%CMD%"=="frontend" GOTO FRONTEND
IF "%CMD%"=="logs"     GOTO LOGS
IF "%CMD%"=="status"   GOTO STATUS
IF "%CMD%"=="down"     GOTO DOWN
IF "%CMD%"=="clean"    GOTO CLEAN
IF "%CMD%"=="clean-all" GOTO CLEAN_ALL

echo [ERREUR] Commande inconnue : %CMD%
echo Usage : run.bat [all^|ollama^|bench^|django^|api^|frontend^|logs^|status^|down^|clean^|clean-all]
EXIT /B 1

REM ── ALL : Ollama + benchmark + API + Frontend ────────────────
:ALL
echo ==============================================
echo  ShopAnalytics — Demarrage complet
echo  Frontend  : http://localhost:5173
echo  API Django: http://localhost:8000/api/
echo  Swagger   : http://localhost:8000/api/docs/
echo  Ollama    : http://localhost:11434
echo ==============================================

docker compose up -d ollama
IF ERRORLEVEL 1 (echo [ERREUR] Impossible de demarrer Ollama. & EXIT /B 1)

echo Attente Ollama pret...
:WAIT_ALL
curl -sf http://localhost:11434/api/tags >NUL 2>&1
IF ERRORLEVEL 1 (
    timeout /t 2 /nobreak >NUL
    GOTO WAIT_ALL
)
echo Ollama pret !

docker compose run --rm benchmark
docker compose up -d django_api frontend

echo.
echo ==============================================
echo  Tout est demarre !
echo  Frontend  : http://localhost:5173
echo  API Django: http://localhost:8000/api/
echo  Swagger   : http://localhost:8000/api/docs/
echo ==============================================
GOTO END

REM ── OLLAMA ──────────────────────────────────────────────────
:OLLAMA
docker compose up -d ollama
GOTO END

REM ── BENCH ───────────────────────────────────────────────────
:BENCH
docker compose run --rm benchmark
GOTO END

REM ── DJANGO ──────────────────────────────────────────────────
:DJANGO
docker compose up --build django_api
GOTO END

REM ── API : Django + Frontend ──────────────────────────────────
:API
docker compose up --build django_api frontend
GOTO END

REM ── FRONTEND ────────────────────────────────────────────────
:FRONTEND
docker compose up frontend
GOTO END

REM ── LOGS ────────────────────────────────────────────────────
:LOGS
docker compose logs -f ollama
GOTO END

REM ── STATUS ──────────────────────────────────────────────────
:STATUS
docker compose ps
GOTO END

REM ── DOWN ────────────────────────────────────────────────────
:DOWN
docker compose down
GOTO END

REM ── CLEAN ───────────────────────────────────────────────────
:CLEAN
del /f /q backend\results\*.json 2>NUL
echo Resultats supprimes.
GOTO END

REM ── CLEAN-ALL ───────────────────────────────────────────────
:CLEAN_ALL
docker compose down -v
del /f /q backend\results\*.json 2>NUL
echo Tout supprime (volumes inclus).
GOTO END

:END