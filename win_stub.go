//go:build !windows

package main

// Stub non-Windows : l'UI s'affiche mais le blocage clavier / anti-veille et le
// passage plein écran multi-moniteur restent à implémenter (X11/Wayland).
type Locker struct{ fgRestore uintptr }

func newLocker() *Locker { return &Locker{} }

func captureForeground() uintptr { return 0 }

func (l *Locker) enter() {}
func (l *Locker) exit()  {}

func (l *Locker) applyHotkey(enabled bool, seq string) bool { return false }
func (l *Locker) shutdown()                                 {}

func bindApp(a *App) {}

func cleanupKillGuards() {}

func monitorFractions() []MonitorFrac {
	return []MonitorFrac{{Fx: 0, Fy: 0, Fw: 1, Fh: 1, Primary: true}}
}
