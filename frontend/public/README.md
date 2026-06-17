# `public/` — Assets statiques

Fichiers servis tels quels par Vite (non transformés par le bundler), copiés à la racine du build de production.

## Fichiers

| Fichier | Description |
|---|---|
| `favicon.png` | Icône de l'onglet navigateur. *(actuellement vide — à remplacer par le logo Anavid avant mise en production)* |
| `manifest.json` | Manifeste PWA (nom de l'app, icônes, couleurs de thème) — permet l'installation de l'app comme application web progressive |

---

## Notes

- Pour ajouter une image statique (logo, illustration), la placer ici et y référer dans le code via un chemin absolu (`/mon-image.png`), sans passer par `import`.
- Le favicon étant actuellement un fichier vide (0 octet), penser à le remplacer par un vrai `.png` ou `.ico` avant le déploiement.
