# `features/chat/` — Assistant IA (Chat RAG)

Écran protégé d'interface conversationnelle avec l'assistant RAG du backend.

## `ChatIA.tsx` + `ChatIA.css` (route `/chat`)

Interface de chat avec l'assistant RAG. Envoie les questions à `POST /api/chat/` (via `API_BASE_URL`), affiche l'historique de conversation et le modèle LLM ayant répondu. S'abonne au `chatBridge` pour recevoir des messages pré-remplis envoyés depuis d'autres écrans (ex. clic sur une notification).

## `chatBridge.ts` — Pont inter-composants

Petit bus d'événements en mémoire (sans dépendance externe) permettant à n'importe quel composant de l'application d'envoyer un message pré-rempli vers `ChatIA.tsx`, même si celui-ci n'est pas encore monté :

```ts
sendToChat("Quel est le flux horaire d'hier ?");
```

| Export | Rôle |
|---|---|
| `registerChatListener(fn)` | Appelé au montage de `ChatIA.tsx` ; délivre immédiatement un message en attente s'il y en a |
| `unregisterChatListener()` | Appelé au démontage de `ChatIA.tsx` |
| `sendToChat(message)` | Envoie un message ; si `ChatIA.tsx` n'est pas monté, le message est mis en attente (`_pending`) et délivré dès le prochain montage |
| `debugBridge()` | Utilitaire de debug — affiche l'état courant du pont dans la console |

**Consommé en dehors de ce domaine par :** `../../components/Notifications.tsx` (clic sur une notification → redirige la question vers le chat) et `../dashboard/Dashboard.tsx`.

## Dépendances transverses utilisées

- `../../services/api.ts` — `API_BASE_URL`

## Pourquoi `chatBridge.ts` est ici plutôt que dans `services/`

`chatBridge.ts` n'est pas un client HTTP : c'est un bus d'événements local à l'application, dont le rôle principal est de communiquer *vers* `ChatIA.tsx`. Il est donc colocalisé avec son principal consommateur. Les autres domaines qui l'utilisent (`Notifications.tsx`, `Dashboard.tsx`) l'importent via un chemin relatif (`../chat/chatBridge`), ce qui est acceptable car peu de domaines en dépendent ; si ce nombre venait à augmenter significativement, ce fichier serait un bon candidat pour remonter dans `services/`.