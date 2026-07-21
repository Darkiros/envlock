# EnvLock 🔒

Verrouilleur d'environnement moderne (PySide6). Affiche un écran plein
animé, bloque les raccourcis clavier d'évasion et empêche la mise en veille —
**sans** verrouiller la session Windows. Déverrouillage par mot de passe.

## Fonctionnalités

- 4 animations au choix, avec **aperçu en direct** : sphère de particules 3D
  (plexus sphere rotatif), réseau de particules, Matrix rain, dégradé fluide.
- Horloge/date optionnelle sur l'écran verrouillé.
- Mot de passe **hashé** (PBKDF2-HMAC-SHA256 + sel, stdlib) dans un fichier de
  config, **modifiable depuis l'application**.
- Blocage clavier bas niveau (Windows) : Alt+Tab, touche Windows, Alt+F4,
  Ctrl+Échap, Ctrl+Maj+Échap…
- Inhibition de la veille écran/système (`SetThreadExecutionState`).

## Installation (Windows)

```powershell
cd envlock
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement

```powershell
python run.py
```

1. Au premier lancement, **définis un mot de passe** dans le panneau.
2. Choisis une animation (aperçu à droite), active/désactive l'horloge.
3. Clique sur **Verrouiller maintenant**.
4. Sur l'écran verrouillé : **Entrée** → saisie du mot de passe → déverrouille.
   (Échap referme le champ sans déverrouiller.)

Le fichier de config est dans `%APPDATA%\EnvLock\config.json`.

## Compiler un .exe (Windows)

> ⚠️ La compilation doit se faire **sur Windows** — PyInstaller produit un
> binaire pour l'OS sur lequel il tourne (pas de cross-compilation depuis WSL).

En un clic :

```powershell
build.bat
```

Ou manuellement :

```powershell
pip install -r requirements-dev.txt
pyinstaller --clean EnvLock.spec
```

Résultat : **`dist\EnvLock.exe`** — un seul fichier, sans fenêtre console.

- Icône optionnelle : place un fichier `assets\envlock.ico` avant le build, il
  sera pris automatiquement (voir `EnvLock.spec`).
- UPX (compression) est activé dans le `.spec` ; si UPX n'est pas installé,
  PyInstaller l'ignore sans erreur.
- Le hook clavier bas niveau (ctypes) fonctionne parfaitement en `.exe`.

## ⚠️ Limite importante

En mode utilisateur (sans driver kernel signé), **Ctrl+Alt+Suppr** ne peut
**pas** être bloqué : c'est la *Secure Attention Sequence*, une protection
volontaire de Windows contre les malwares. Tout le reste est bloqué. Pour
couvrir aussi Ctrl+Alt+Suppr il faudrait un *credential provider* ou un driver
— lourd, à éviter pour un usage perso.

## Portage Linux (plus tard)

`platform_lock.py` contient déjà un `NoopLocker` : l'écran s'affiche sur Linux
mais le blocage clavier natif reste à implémenter (X11 `XGrabKeyboard` /
inhibiteur de veille D-Bus). Tout le reste (UI, animations, mot de passe) est
déjà cross-platform.

## Structure

```
envlock/
├── run.py                  # lanceur
├── requirements.txt
├── requirements-dev.txt    # + pyinstaller
├── EnvLock.spec            # config de build PyInstaller
├── build.bat               # build .exe en un clic (Windows)
└── envlock/
    ├── main.py             # orchestration panneau <-> écran verrouillé
    ├── config.py           # config JSON + hachage mot de passe
    ├── platform_lock.py    # hook clavier + anti-veille (Windows / stub Linux)
    ├── control_panel.py    # UI de réglage + aperçu
    ├── lock_window.py      # écran verrouillé + prompt mot de passe
    ├── style.py            # thème sombre (QSS)
    └── animations/
        ├── base.py         # QWidget animé ~30 fps
        ├── particles.py
        ├── matrix.py
        └── gradient.py
```
