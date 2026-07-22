# EnvLock 🔒

Verrouilleur d'environnement moderne pour Windows, écrit en **Go + [Wails](https://wails.io)**.
Affiche un écran plein animé, bloque les raccourcis clavier d'évasion et empêche
la mise en veille — **sans** verrouiller la session Windows. Déverrouillage par
mot de passe.

Binaire natif d'environ **9 Mo**, sans dépendance à installer (hors runtime
WebView2, présent d'office sur Windows 10 récent / 11).

## Fonctionnalités

- **Écran de verrouillage plein écran multi-moniteur** : couvre tous les écrans,
  une animation par moniteur, horloge + prompt centrés sur l'écran principal.
- **4 animations** avec aperçu en direct :
  - *Orbe de particules* (façon JARVIS) — réglable finement (sliders : densité,
    amplitude/vitesse des vagues, rotation, taille des points, teinte, pulsation).
  - *Réseau de particules*, *Matrix rain*, *Dégradé fluide*.
- **Mot de passe hashé** (PBKDF2-HMAC-SHA256 + sel) dans un fichier de config,
  modifiable depuis l'application.
- **Blocage clavier bas niveau** (`WH_KEYBOARD_LL`) : Alt+Tab, touche Windows,
  Alt+F4, Ctrl+Échap, Ctrl+Maj+Échap, Alt+Espace, touche menu…
- **Inhibition de la veille** écran et système (`SetThreadExecutionState`).
- **Watchdog premier plan** : réaffirme le topmost toutes les 400 ms si une autre
  fenêtre tente de passer devant.
- **Barre de notification (systray)** : menu Ouvrir / Verrouiller / Quitter,
  fermeture de la fenêtre = réduction dans la barre.
- **Raccourci global configurable** (`Ctrl+Alt+L` par défaut) : verrouille à tout
  moment, même application réduite.
- **Curseur masqué** pendant l'animation (réaffiché sur le prompt).
- *(Optionnel, si lancé en administrateur)* désactive le Gestionnaire des tâches
  pendant le verrouillage (`DisableTaskMgr`, restauré au déverrouillage).

## ⚠️ Limites (mode utilisateur)

Impossible à contourner sans driver kernel / credential provider signé :

- **Ctrl+Alt+Suppr** (Secure Attention Sequence) ne peut pas être bloqué ni
  couvert — protection anti-malware volontaire de Windows. Depuis cet écran on
  peut *Se déconnecter* / *Changer d'utilisateur* (ferme la session).
- La désactivation du Gestionnaire des tâches nécessite de lancer EnvLock **en
  administrateur** ; sur un poste géré par GPO d'entreprise, la clé de policy peut
  être verrouillée en écriture (l'app le détecte et n'échoue pas).

## Télécharger

Chaque push produit un binaire via GitHub Actions :

- Onglet **Actions** → dernier run *Build Windows exe* → artefact **`EnvLock-windows`**
  (contient `EnvLock.exe` et `EnvLock-debug.exe`).
- Ou en ligne de commande : `gh run download -n EnvLock-windows`.
- Une version taggée (`git tag v1.0.0 && git push --tags`) attache `EnvLock.exe`
  à une **Release** GitHub.

`EnvLock-debug.exe` ouvre une console (diagnostic) ; `EnvLock.exe` est la version
normale.

## Compiler depuis les sources

Prérequis : [Go](https://go.dev) ≥ 1.23 et la CLI Wails.

```bash
go install github.com/wailsapp/wails/v2/cmd/wails@latest
wails build -platform windows/amd64 -s -o EnvLock.exe
# -> build/bin/EnvLock.exe
```

`-s` saute l'étape frontend (les assets HTML/JS statiques sont déjà dans
`frontend/dist/` et embarqués via `//go:embed`).

Développement rapide : `wails dev`.

## Utilisation

1. Au premier lancement, **définir un mot de passe**.
2. Choisir une animation (aperçu à droite) ; pour l'orbe, ajuster les sliders.
3. **Verrouiller** via le bouton, le menu du systray, ou le raccourci global.
4. Sur l'écran verrouillé : **Entrée** → saisir le mot de passe → déverrouille.
   (Échap referme le champ.)

Config : `%APPDATA%\EnvLock\config.json` (mot de passe hashé, animation, réglages
de l'orbe, raccourci, options).

## Architecture

Go possède toute l'intégration Win32 (fenêtre message cachée + `WndProc` sur une
goroutine dédiée à boucle de messages) : hook clavier, systray, raccourci,
anti-veille, plein écran multi-moniteur. La **WebView** (WebView2) affiche l'UI
(HTML/Canvas). Les deux communiquent via les bindings Wails.

```
envlock/
├── main.go              # point d'entrée Wails + embed du frontend
├── app.go               # bindings exposés au frontend (JS <-> Go)
├── config.go            # config JSON + hachage du mot de passe
├── logutil.go           # log de diagnostic (%APPDATA%\EnvLock\envlock.log)
├── win_lock.go          # hook clavier, anti-veille, plein écran, moniteurs (Windows)
├── win_tray.go          # fenêtre cachée, systray, menu, raccourci global (Windows)
├── win_stub.go          # stubs non-Windows
├── wails.json           # config Wails
├── build/appicon.png    # icône (orbe) -> icône exe + systray
└── frontend/dist/       # UI embarquée
    ├── index.html
    ├── app.js           # logique panneau <-> verrouillage
    └── animations.js    # les 4 animations (canvas 2D)
```

## Portage Linux (plus tard)

`win_stub.go` fournit des stubs : l'UI s'affiche mais le blocage clavier natif,
l'anti-veille, le systray et le plein écran multi-moniteur restent à implémenter
(X11/Wayland, D-Bus). Toute la logique UI, animations et mot de passe est déjà
portable.
