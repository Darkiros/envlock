package main

import (
	"context"

	wailsruntime "github.com/wailsapp/wails/v2/pkg/runtime"
)

// App expose les méthodes appelables depuis le frontend (WebView).
type App struct {
	ctx              context.Context
	config           Config
	locker           *Locker
	locked           bool
	hidden           bool    // fenêtre réduite dans la barre de notification
	lockedFromHidden bool    // l'app était-elle dans la barre au moment du lock ?
	prevForeground   uintptr // fenêtre au premier plan avant le verrouillage
}

func NewApp() *App {
	return &App{config: loadConfig()}
}

func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
	a.locker = newLocker()
	bindApp(a)
	cleanupKillGuards() // restaure une éventuelle policy laissée par un crash
	go a.locker.applyHotkey(a.config.Hotkey.Enabled, a.config.Hotkey.Sequence)
	logf("startup ok — webview initialisée")
}

// ---- config / mot de passe (bindings JS) ----------------------------

func (a *App) GetConfig() Config { return a.config }

func (a *App) HasPassword() bool { return a.config.Password != nil }

func (a *App) SetPassword(pw string) error {
	a.config.Password = hashPassword(pw)
	return a.config.save()
}

func (a *App) VerifyPassword(pw string) bool {
	return a.config.Password.verify(pw)
}

func (a *App) SaveConfig(c Config) error {
	// On préserve le hash existant (le frontend ne le renvoie pas).
	c.Password = a.config.Password
	a.config = c
	return c.save()
}

func (a *App) SetAnimation(name string) error {
	a.config.Animation = name
	return a.config.save()
}

func (a *App) SetClock(on bool) error {
	a.config.Clock = on
	return a.config.save()
}

// SetSphere fusionne les réglages de l'orbe (sliders) et sauvegarde.
func (a *App) SetSphere(opts map[string]float64) error {
	if a.config.Sphere == nil {
		a.config.Sphere = map[string]float64{}
	}
	for k, v := range opts {
		a.config.Sphere[k] = v
	}
	return a.config.save()
}

// MonitorFrac : géométrie d'un moniteur exprimée en fractions [0..1] du
// bureau virtuel (indépendant du DPI côté frontend).
type MonitorFrac struct {
	Fx      float64 `json:"fx"`
	Fy      float64 `json:"fy"`
	Fw      float64 `json:"fw"`
	Fh      float64 `json:"fh"`
	Primary bool    `json:"primary"`
}

// GetMonitors renvoie la disposition des écrans (pour dessiner un orbe par
// moniteur et centrer le prompt sur l'écran principal).
func (a *App) GetMonitors() []MonitorFrac {
	return monitorFractions()
}

// ---- verrouillage ---------------------------------------------------

// Lock étend la fenêtre sur tout le bureau virtuel, la met au premier plan,
// installe le hook clavier et empêche la veille.
func (a *App) Lock() {
	a.prevForeground = captureForeground() // AVANT d'afficher/voler le focus
	a.lockedFromHidden = a.hidden
	a.locked = true
	wailsruntime.WindowShow(a.ctx)
	a.hidden = false
	a.locker.enter()
}

// Unlock lève le blocage et rend la main dans l'état précédent : si le
// verrouillage a été déclenché alors que l'app était dans la barre, on y
// retourne au lieu d'afficher le panneau.
func (a *App) Unlock() {
	a.locker.fgRestore = a.prevForeground // rendre le premier plan à l'appli d'avant
	a.locker.hideOnExit = a.lockedFromHidden
	a.locker.exit()
	a.locked = false
	if a.lockedFromHidden {
		a.hidden = true
		wailsruntime.WindowHide(a.ctx)
	}
}

// HideToTray réduit la fenêtre dans la barre de notification (suivi côté Go).
func (a *App) HideToTray() {
	a.hidden = true
	wailsruntime.WindowHide(a.ctx)
}

func (a *App) SetHotkey(enabled bool, sequence string) bool {
	a.config.Hotkey.Enabled = enabled
	a.config.Hotkey.Sequence = sequence
	_ = a.config.save()
	return a.locker.applyHotkey(enabled, sequence)
}

func (a *App) SetMinimizeToTray(on bool) error {
	a.config.MinimizeToTray = on
	return a.config.save()
}

// ---- appelés depuis le tray / le raccourci (côté Go) ----------------
func (a *App) showWindow() {
	a.hidden = false
	wailsruntime.WindowShow(a.ctx)
	wailsruntime.WindowUnminimise(a.ctx)
}

func (a *App) hotkeyLock() {
	if a.locked {
		return
	}
	// On n'affiche PAS ici : Lock() (déclenché par le frontend) capture d'abord
	// l'état "caché" puis affiche, pour pouvoir y revenir au déverrouillage.
	wailsruntime.EventsEmit(a.ctx, "trigger-lock")
}

func (a *App) quitApp() {
	a.locker.shutdown()
	wailsruntime.Quit(a.ctx)
}
