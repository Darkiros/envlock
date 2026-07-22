package main

import "context"

// App expose les méthodes appelables depuis le frontend (WebView).
type App struct {
	ctx    context.Context
	config Config
	locker *Locker
}

func NewApp() *App {
	return &App{config: loadConfig()}
}

func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
	a.locker = newLocker()
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

// ---- verrouillage ---------------------------------------------------

// Lock étend la fenêtre sur tout le bureau virtuel, la met au premier plan,
// installe le hook clavier et empêche la veille.
func (a *App) Lock() { a.locker.enter() }

// Unlock restaure la fenêtre et lève le blocage.
func (a *App) Unlock() { a.locker.exit() }
