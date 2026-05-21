# `rappel` — Design Spec

**Date** : 2026-05-21
**Auteur** : Bryan Chen
**Statut** : Design approuvé, en attente de plan d'implémentation

## Résumé en une phrase

`rappel` est une app desktop Linux open source, à l'esthétique cozy/lo-fi, qui envoie des rappels système personnalisables (boire, faire une pause, étirements, etc.) et trace la complétion dans une interface web locale visuellement immersive.

## Public cible

Développeurs (et plus largement, knowledge workers) sur Linux qui veulent prendre soin de leur santé sans installer une app productivity bourrée de notifs agressives. L'app doit donner envie d'être ouverte pour la beauté de l'interface, pas seulement parce qu'on y est obligé.

## Décisions clés

| Décision | Choix | Raison |
|---|---|---|
| Plateforme | Desktop Linux (GNOME/Wayland en cible primaire) | Cible utilisateur immédiate ; gratuit à distribuer |
| Scope v1 | Tracking complet + objectifs + stats | Demandé explicitement par l'utilisateur |
| Type de rappels | Personnalisables multiples (générique) | Pas spécifique à l'eau ; cas d'usage = eau, yeux, étirements, médicaments, etc. |
| Interface principale | Mini-serveur web local (`localhost:8765`) | Portable, jolie facilement, futur-proof pour accès mobile sur LAN |
| Esthétique | Cozy/lo-fi à la studywithme.io (scènes ambient + glassmorphism) | Critère explicite utilisateur |
| Licence | MIT | Standard open source, permissive |

## Architecture

### Vue d'ensemble

Un seul process Python qui combine serveur web (FastAPI) + scheduler de rappels (APScheduler) + notifier desktop (`desktop-notifier`). Stockage local SQLite.

```
┌─────────────────────────────────────────────────────────────┐
│                  rappel (process unique)                     │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐   ┌───────────────┐  │
│  │  Web Router  │    │   Scheduler  │   │   Notifier    │  │
│  │  (FastAPI)   │    │ (APScheduler)│   │(desktop-notif)│  │
│  └──────┬───────┘    └──────┬───────┘   └───────▲───────┘  │
│         │                   │                   │           │
│         │  HTTP             │  triggers         │ async     │
│         ▼                   ▼                   │           │
│  ┌──────────────────────────────────────────────┴────────┐ │
│  │              ReminderService (core logic)             │ │
│  └────────────────────────┬──────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│  ┌────────────────────────────────────────────────────────┐│
│  │         Repository (SQLite via sqlite3 stdlib)         ││
│  └────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
         │                                       ▲
         │ serves HTML                           │ POST /events
         ▼                                       │
┌─────────────────────┐               ┌──────────────────────┐
│   Browser (user)    │               │  Desktop notification│
│   localhost:8765    │               │   (click → callback) │
└─────────────────────┘               └──────────────────────┘
```

### Modules

| Module | Responsabilité | Dépend de |
|---|---|---|
| `rappel/web.py` | Routes FastAPI, sert templates Jinja | `service` |
| `rappel/scheduler.py` | Boucle APScheduler, planifie/replanifie les jobs | `service`, `notifier` |
| `rappel/notifier.py` | Wrapper `desktop-notifier` + callbacks d'actions | — |
| `rappel/service.py` | Logique métier (rappels, logs, stats) | `repository` |
| `rappel/repository.py` | CRUD SQLite, migrations | — |
| `rappel/models.py` | Dataclasses (Reminder, Event) | — |
| `rappel/cli.py` | Point d'entrée `rappel` (start, status, install, stop) | `web`, `scheduler` |
| `rappel/templates/` | HTML Jinja2 (HTMX) | — |
| `rappel/static/` | CSS custom + Tailwind build + JS scènes | — |

### Boundaries clés

- **`notifier` ignore la DB** : reçoit `(title, body, actions, callback)`. Permet de tester sans système de notif et de remplacer le backend plus tard.
- **`scheduler` ignore HTTP** : consomme `service` et `notifier`. Permet un mode CLI headless futur.
- **`repository` est isolé derrière une interface simple** : si on change de moteur (Postgres ?), seul ce fichier bouge.

## Data Model

### Tables SQLite

```sql
CREATE TABLE reminders (
  id                 INTEGER PRIMARY KEY,
  name               TEXT NOT NULL,
  message            TEXT NOT NULL,
  icon               TEXT,                            -- emoji ou nom freedesktop
  interval_minutes   INTEGER NOT NULL,
  active_hours_start TEXT NOT NULL DEFAULT '09:00',   -- "HH:MM"
  active_hours_end   TEXT NOT NULL DEFAULT '18:00',
  active_days        TEXT NOT NULL DEFAULT 'mon,tue,wed,thu,fri',
  enabled            INTEGER NOT NULL DEFAULT 1,
  tracked            INTEGER NOT NULL DEFAULT 0,
  unit_label         TEXT,                            -- "verre", "ml"
  unit_amount        INTEGER,                         -- ex: 250
  daily_goal         INTEGER,                         -- ex: 8
  created_at         TEXT NOT NULL,
  paused_until       TEXT
);

CREATE TABLE events (
  id          INTEGER PRIMARY KEY,
  reminder_id INTEGER NOT NULL REFERENCES reminders(id) ON DELETE CASCADE,
  occurred_at TEXT NOT NULL,
  kind        TEXT NOT NULL CHECK(kind IN ('fired', 'acked', 'snoozed', 'dismissed')),
  value       INTEGER  -- pour 'acked' : quantité
);
CREATE INDEX idx_events_reminder_time ON events(reminder_id, occurred_at);

CREATE TABLE settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

### Settings par défaut

```python
DEFAULT_SETTINGS = {
    'snooze_minutes': '10',
    'notification_timeout_seconds': '30',
    'theme': 'auto',
}
```

### Dataclasses Python

```python
@dataclass
class Reminder:
    id: int | None
    name: str
    message: str
    icon: str | None
    interval_minutes: int
    active_hours: tuple[time, time]
    active_days: frozenset[Weekday]
    enabled: bool
    tracked: bool
    unit_label: str | None
    unit_amount: int | None
    daily_goal: int | None
    created_at: datetime
    paused_until: datetime | None

@dataclass
class Event:
    id: int | None
    reminder_id: int
    occurred_at: datetime
    kind: Literal['fired', 'acked', 'snoozed', 'dismissed']
    value: int | None
```

### Choix de design

- **Pas d'ORM** : `sqlite3` stdlib + queries SQL explicites. ~10 fonctions dans `repository.py`.
- **Events immuables** : on n'UPDATE jamais, seulement INSERT. Simplifie + permet replay/debug.
- **`active_hours` / `active_days`** : évite le spam nuit/weekend.
- **`paused_until` séparé de `enabled`** : distingue désactivation longue vs pause courte.

## Flux de notification

### Flux nominal

```
[APScheduler tick]
       │
       ▼
service.fire_reminder(reminder_id)
       │
       ├─► verify is_in_active_window + not paused
       ├─► repository.insert_event(reminder_id, 'fired')
       │
       ▼
notifier.notify(title, body, actions=[
       ('ack',     'Fait ✓'),
       ('snooze',  'Snooze 10min'),
   ], on_action=callback)
       │
       ▼  [D-Bus → org.freedesktop.Notifications]
       │
       ▼ (user click ou timeout)
       │
callback(action_id) reçue par notifier
       │
       ▼
service.handle_action(reminder_id, action_id)
       │
       ├─ 'ack'     → insert_event('acked', value=unit_amount)
       ├─ 'snooze'  → insert_event('snoozed') + scheduler.schedule_once(+snooze_min)
       └─ aucun     → insert_event('dismissed') après notification_timeout
```

### Choix techniques

- **`desktop-notifier`** plutôt que `notify-send` subprocess : async natif, callbacks propres, cross-DE.
- **Synchronisation du scheduler** : à chaque CREATE/UPDATE/DELETE d'un rappel, on appelle `scheduler.sync_jobs()`. Coût O(n) négligeable (n < 20).
- **Filtre `active_hours` côté service** plutôt que cron triggers complexes : le scheduler tire à l'intervalle, `fire_reminder` filtre.
- **`coalesce=True`** sur APScheduler : si la machine était endormie, on ne rejoue PAS les jobs manqués (évite le spam au réveil).

### Cas d'erreur

| Scénario | Comportement |
|---|---|
| `desktop-notifier` ne peut joindre D-Bus | Log warning, skip cette notif (pas de crash) |
| Notif envoyée mais GNOME affiche pas (DND) | OK, l'event `fired` est quand même loggué |
| Machine endormie 4h | `coalesce=True` évite le spam au réveil |
| Crash en plein milieu d'un snooze | Au redémarrage, `sync_jobs()` ignore les snoozes en cours, retour au cycle normal |
| Action arrive après suppression du rappel | `handle_action` vérifie existence, log + ignore sinon |

## Web UI esthétique

### Vibe générale

`rappel` est une fenêtre ouverte sur une scène apaisante. Le tracking est intégré à l'ambiance, pas au premier plan. L'utilisateur ouvre l'onglet pour la beauté, et voit ses stats par effet de bord.

### Stack frontend

- **Templates Jinja2** (server-rendered)
- **HTMX** (CDN, ~14KB) pour interactions sans page reload
- **Tailwind CSS** (build statique committé, pas de Node requis pour utilisateurs)
- **CSS custom** (`static/rappel.css`) pour glassmorphism + animations
- **Canvas JS léger** (~80 LOC) pour particules par scène
- **Google Fonts** : Fraunces (display serif) + Inter (UI)

### Pages & routes

```
GET  /                         → Dashboard (page principale)
GET  /reminders                → Liste/gestion
GET  /reminders/new            → Form création
POST /reminders                → Créer
GET  /reminders/{id}/edit      → Form édition
POST /reminders/{id}           → Update (HTMX)
POST /reminders/{id}/delete    → Delete
POST /reminders/{id}/toggle    → Enable/disable (HTMX)
POST /reminders/{id}/pause     → Pause (1h, today, custom)
GET  /stats                    → Statistiques détaillées
GET  /settings                 → Préférences globales
POST /settings                 → Update
POST /api/events               → Logger event (ack/snooze/dismiss)
GET  /api/health               → Healthcheck (systemd)
```

### Scènes ambient (v1)

Chaque scène est un module CSS+Canvas autonome dans `static/scenes/`. Aucun fichier vidéo dans le repo.

| Scène | Description | Palette |
|---|---|---|
| 🌧 **Rainy window** | Gouttes ruisselant sur vitre, ciel gris-bleu | `#1a2332` → `#3d556e`, accents `#e8d5a8` |
| 🌊 **Ocean depth** | Bulles montant lentement, rayons diagonaux | `#0a2540` → `#1e5780`, particules blanc 30% |
| 🌅 **Sunset beach** | Vagues animées, ciel orange/rose/violet | `#fdb585` → `#c66a8e` → `#5c4a7a` |
| 🌲 **Forest stream** | Feuilles tombant doucement, vert tamisé | `#2d3e2f` → `#5a7a5d`, particules ambrées |
| 🌌 **Calm night** | Étoiles scintillantes, lune, nuit profonde | `#0c1024` → `#252a4a`, étoiles `#fff8d9` |

### Layout principal

Scène plein écran + panneau glassmorphism centré :

```
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   [Scène d'arrière-plan animée plein écran]             ║
║                                                          ║
║                                          🌊 Ocean ▾   ⚙  ║
║                                                          ║
║          ┌─────────────────────────────────┐            ║
║          │   [glassmorphism panneau]       │            ║
║          │      mardi 21 mai · 14:32       │            ║
║          │                                  │            ║
║          │            💧                    │            ║
║          │           Eau                    │            ║
║          │   ━━━━━━━━━━○────  6 / 8         │            ║
║          │   prochain rappel dans 23 min   │            ║
║          │                                  │            ║
║          │   [ +1 verre ]   [ pause ]      │            ║
║          │                                  │            ║
║          │   Autres rappels                 │            ║
║          │   👀 Pause yeux  • 4/4           │            ║
║          │   🦵 Étire-toi   • dans 12 min   │            ║
║          │                                  │            ║
║          │       → voir les stats           │            ║
║          └─────────────────────────────────┘            ║
║                                                          ║
║                                                  ♪ ───   ║
╚══════════════════════════════════════════════════════════╝
```

**Panneau central** :
- `backdrop-filter: blur(20px) saturate(140%)`
- `background: rgba(255,255,255,0.08)` adapt selon luminosité scène
- `border: 1px solid rgba(255,255,255,0.18)`
- `border-radius: 24px`
- `box-shadow: 0 8px 32px rgba(0,0,0,0.2)`
- `padding: 48px`, `max-width: 480px`, centré

### Typographie

```css
--font-display: 'Fraunces', 'Playfair Display', Georgia, serif;
--font-ui:      'Inter', system-ui, sans-serif;
--font-mono:    'JetBrains Mono', ui-monospace, monospace;
```

### Player lo-fi (optionnel)

Mini-pill flottante bas-droite. Sources : Pixabay Music CC0, téléchargées au premier launch dans `~/.cache/rappel/sounds/`.

Pistes v1 : Pluie, Vagues, Café lo-fi, (silence).

### Animations

- Bouton "+1" : splash sur clic (transform + opacity, 600ms ease)
- Switch de scène : crossfade 800ms entre canvas
- Apparition panneau : `opacity 0→1 + translateY(20px→0)` au load
- Particules canvas : `requestAnimationFrame` capped 30fps
- Pause animations si onglet en background
- `prefers-reduced-motion` → désactive particules

### Sécurité

L'app écoute sur `127.0.0.1` uniquement. Pas d'auth pour la v1. Accès LAN/mobile sera ajouté plus tard avec token.

## Configuration & persistence

### Emplacements XDG

```
~/.config/rappel/
  └─ config.toml          # config user (port, scène par défaut)

~/.local/share/rappel/
  ├─ rappel.db            # SQLite
  └─ rappel.db.backup-*   # backups quotidiens, garde 7 derniers

~/.cache/rappel/
  ├─ sounds/              # audio téléchargé au runtime
  └─ logs/
     └─ rappel.log        # rotation à 5MB, garde 3 fichiers

~/.config/systemd/user/
  └─ rappel.service       # créé par `rappel install`
```

### `config.toml`

```toml
[server]
host = "127.0.0.1"
port = 8765

[ui]
default_scene = "ocean-depth"
ambient_sound = "ocean"  # ou "off"
theme = "auto"

[paths]
# Override possible
# data_dir = "/path/to/custom"
```

Tout le reste (snooze, intervalles…) dans la table `settings` SQLite, éditable via UI web.

### Migrations SQLite

Approche simple, ~10 LOC :

```python
SCHEMA_VERSION = 1

MIGRATIONS = {
    1: """
        CREATE TABLE reminders (...);
        CREATE TABLE events (...);
        CREATE TABLE settings (...);
        CREATE INDEX idx_events_reminder_time ON events(reminder_id, occurred_at);
    """,
}

def migrate(conn):
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for version in range(current + 1, SCHEMA_VERSION + 1):
        conn.executescript(MIGRATIONS[version])
        conn.execute(f"PRAGMA user_version = {version}")
```

### Backups

Au démarrage si dernier backup > 24h : copie de `rappel.db`, suppression des > 7 jours.

## Packaging & installation

### Distribution

Python package via `pyproject.toml`, publié sur PyPI sous le nom **`rappel`** (vérifier dispo au premier publish ; fallback `rappel-app`).

```toml
[project]
name = "rappel"
version = "0.1.0"
description = "Un rappel cozy pour les devs : eau, yeux, étirements."
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "apscheduler>=3.10",
    "desktop-notifier>=4.0",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
]

[project.scripts]
rappel = "rappel.cli:main"
```

### Installation utilisateur

```bash
# Recommandé
pipx install rappel
rappel install      # crée + enable le service systemd user
rappel start        # démarre
# → http://localhost:8765
```

### Sous-commandes CLI

```
rappel start         # lance le serveur
rappel stop          # arrête le service systemd
rappel status        # status + URL
rappel install       # crée + enable le service systemd user
rappel uninstall     # supprime le service (garde les données)
rappel purge         # supprime données aussi (avec confirmation)
rappel version
rappel logs          # tail des logs
```

Implémentées avec `argparse` (stdlib).

### Service systemd user

Généré par `rappel install` :

```ini
[Unit]
Description=rappel reminder service
After=graphical-session.target

[Service]
Type=simple
ExecStart=%h/.local/bin/rappel start
Restart=on-failure
RestartSec=5s
Environment="RAPPEL_MANAGED_BY_SYSTEMD=1"

[Install]
WantedBy=default.target
```

### Structure du dépôt

```
rappel/
├── rappel/                   # package Python
│   ├── __init__.py
│   ├── cli.py
│   ├── web.py
│   ├── scheduler.py
│   ├── notifier.py
│   ├── service.py
│   ├── repository.py
│   ├── models.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── reminders.html
│   │   ├── stats.html
│   │   └── settings.html
│   ├── static/
│   │   ├── rappel.css        # custom styles
│   │   ├── tailwind.css      # build statique committé
│   │   ├── rappel.js         # HTMX helpers
│   │   ├── scenes/           # un .js par scène
│   │   ├── icons/            # PNG 256x256
│   │   └── sounds/           # downloaded runtime, gitignored
│   └── data/
│       └── default_reminders.json
├── tests/
│   ├── test_repository.py
│   ├── test_service.py
│   ├── test_scheduler.py
│   ├── test_notifier.py
│   └── test_web.py
├── docs/
│   ├── INSTALL.md
│   ├── CONTRIBUTING.md
│   ├── ADDING_A_SCENE.md
│   └── screenshots/
├── pyproject.toml
├── README.md
├── LICENSE                   # MIT
└── .github/
    ├── workflows/ci.yml
    └── ISSUE_TEMPLATE/
```

### CI minimale

GitHub Actions : `ruff check`, `mypy rappel/`, `pytest tests/` (Python 3.11/3.12/3.13).

### Stratégie de tests

| Module | Type | Comment |
|---|---|---|
| `repository.py` | Unit | SQLite `:memory:` |
| `service.py` | Unit | DI du repo |
| `scheduler.py` | Unit | `freezegun` pour temps mockés |
| `notifier.py` | Unit | `FakeNotifier` |
| `web.py` | Integration | `httpx.AsyncClient` |
| End-to-end | Skip v1 | Trop complexe (D-Bus + browser) |

Cible : ~80% coverage logique métier.

### README & onboarding contributeur

Structure :
1. Hero GIF (dashboard avec bulles)
2. Tagline : "Un rappel cozy pour les devs : eau, yeux, étirements."
3. Install (3 lignes)
4. Screenshots (les 5 scènes)
5. Features (bullets courts)
6. CTA contributing : `docs/ADDING_A_SCENE.md` (1 fichier JS à ajouter)

## Risques & questions ouvertes

| Risque | Mitigation |
|---|---|
| Nom `rappel` indispo sur PyPI | Fallback `rappel-app` ; vérifier au premier publish |
| `desktop-notifier` callbacks ne marchent pas sur certains DE non-GNOME | Tester sur Plasma/XFCE en early-access ; fallback notif sans action (log via UI uniquement) |
| GNOME Wayland sans tray icon | Pas un problème : on n'a pas de tray. L'accès se fait via URL ou bookmark. |
| Sons audio (3-4MB total) téléchargés au premier launch | Faire opt-in : ambient sound désactivé par défaut, l'utilisateur l'active depuis settings, ce qui déclenche le download |
| Audit RGPD / data | App 100% locale, aucun analytics, aucun call externe sauf download initial des sons (depuis Pixabay) |

## Non-objectifs (explicitement hors scope v1)

- Apps mobiles (iOS/Android)
- Synchronisation cloud
- Profils multiples (mode travail / weekend)
- Snooze configurable par rappel (un global suffit)
- Notifications email/SMS
- Plugin/scripting custom
- Intégrations tierces (calendrier, fitness trackers)
- i18n complète (FR par défaut, anglais en best-effort dans la v1)
- Windows / macOS support (focus Linux pour v1)

Ces items peuvent être discutés pour la v2 selon adoption.
