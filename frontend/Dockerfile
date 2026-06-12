# ============================================================
# anavidApp — Ionic React (Vite) — Dev only
# ============================================================
FROM node:20-alpine

WORKDIR /app

# Copie des manifestes en premier (cache layer)
COPY package.json package-lock.json ./
RUN npm ci

# Le code source est monté via volume en dev
# (COPY . . n'est pas nécessaire ici — le volume le couvre)

EXPOSE 5173

CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "5173"]