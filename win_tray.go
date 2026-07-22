//go:build windows

package main

import (
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

var (
	shell32 = syscall.NewLazyDLL("shell32.dll")

	pGetModuleHandleW    = kernel32.NewProc("GetModuleHandleW")
	pGetModuleFileNameW  = kernel32.NewProc("GetModuleFileNameW")
	pRegisterClassExW    = user32.NewProc("RegisterClassExW")
	pCreateWindowExW     = user32.NewProc("CreateWindowExW")
	pDefWindowProcW      = user32.NewProc("DefWindowProcW")
	pGetMessageW         = user32.NewProc("GetMessageW")
	pPostMessageW        = user32.NewProc("PostMessageW")
	pPostQuitMessage     = user32.NewProc("PostQuitMessage")
	pCreatePopupMenu     = user32.NewProc("CreatePopupMenu")
	pAppendMenuW         = user32.NewProc("AppendMenuW")
	pTrackPopupMenu      = user32.NewProc("TrackPopupMenu")
	pDestroyMenu         = user32.NewProc("DestroyMenu")
	pGetCursorPos        = user32.NewProc("GetCursorPos")
	pSetForegroundWindow = user32.NewProc("SetForegroundWindow")
	pRegisterHotKey      = user32.NewProc("RegisterHotKey")
	pUnregisterHotKey    = user32.NewProc("UnregisterHotKey")
	pLoadIconW           = user32.NewProc("LoadIconW")
	pGetForegroundWindow = user32.NewProc("GetForegroundWindow")
	pShellNotifyIconW    = shell32.NewProc("Shell_NotifyIconW")
	pExtractIconW        = shell32.NewProc("ExtractIconW")
)

const (
	wmApp           = 0x8000
	msgTrayCallback = wmApp + 1
	msgEnter        = wmApp + 2
	msgExit         = wmApp + 3
	msgSetHotkey    = wmApp + 4
	msgReassert     = wmApp + 5

	swpNoSize     = 0x0001
	swpNoMove     = 0x0002
	swpNoActivate = 0x0010

	wmHotkey        = 0x0312
	wmCommand       = 0x0111
	wmDestroy       = 0x0002
	wmRButtonUp     = 0x0205
	wmLButtonDblClk = 0x0203
	wmLButtonUp     = 0x0202

	nimAdd     = 0
	nimDelete  = 2
	nifMessage = 0x01
	nifIcon    = 0x02
	nifTip     = 0x04

	idOpen = 0x101
	idLock = 0x102
	idQuit = 0x103

	mfString    = 0x0000
	mfSeparator = 0x0800
	tpmRight    = 0x0002

	hotkeyID       = 1
	modAlt         = 0x0001
	modControl     = 0x0002
	modShift       = 0x0004
	modWin         = 0x0008
	modNoRepeat    = 0x4000
	idiApplication = 32512
)

type wndClassEx struct {
	CbSize        uint32
	Style         uint32
	LpfnWndProc   uintptr
	CbClsExtra    int32
	CbWndExtra    int32
	HInstance     uintptr
	HIcon         uintptr
	HCursor       uintptr
	HbrBackground uintptr
	LpszMenuName  *uint16
	LpszClassName *uint16
	HIconSm       uintptr
}

type notifyIconData struct {
	CbSize           uint32
	HWnd             uintptr
	UID              uint32
	UFlags           uint32
	UCallbackMessage uint32
	HIcon            uintptr
	SzTip            [128]uint16
	DwState          uint32
	DwStateMask      uint32
	SzInfo           [256]uint16
	UTimeoutVersion  uint32
	SzInfoTitle      [64]uint16
	DwInfoFlags      uint32
	GuidItem         [16]byte
	HBalloonIcon     uintptr
}

// Locker : intégration Win32 sur une goroutine dédiée (fenêtre cachée +
// boucle de messages, indispensable au hook clavier, au tray et au raccourci).
type Locker struct {
	msgHwnd   uintptr
	hwnd      uintptr // fenêtre Wails (cible du plein écran)
	prev      rect
	hook      uintptr
	ready     chan struct{}
	tooltip   string
	stopWatch chan struct{}
	fgRestore uintptr // fenêtre à remettre au premier plan au déverrouillage
}

var theLocker *Locker
var theApp *App

// Résultat de l'enregistrement du raccourci, renvoyé par le thread worker.
var hkResult = make(chan bool, 1)

func newLocker() *Locker {
	l := &Locker{ready: make(chan struct{}), tooltip: "EnvLock"}
	theLocker = l
	go l.worker()
	return l
}

func bindApp(a *App) { theApp = a }

func utf16Ptr(s string) *uint16 {
	p, _ := syscall.UTF16PtrFromString(s)
	return p
}

func copyUTF16(dst []uint16, s string) {
	u, err := syscall.UTF16FromString(s)
	if err == nil {
		copy(dst, u)
	}
}

func (l *Locker) worker() {
	runtime.LockOSThread()
	l.createWindow()
	l.addTray()
	close(l.ready)

	var m msg
	for {
		r, _, _ := pGetMessageW.Call(uintptr(unsafe.Pointer(&m)), 0, 0, 0)
		if int32(r) <= 0 { // 0 = WM_QUIT, -1 = erreur
			break
		}
		pTranslateMessage.Call(uintptr(unsafe.Pointer(&m)))
		pDispatchMessageW.Call(uintptr(unsafe.Pointer(&m)))
	}
	l.removeTray()
}

var wndProcPtr = syscall.NewCallback(wndProc)

func wndProc(hwnd, umsg, wparam, lparam uintptr) uintptr {
	switch umsg {
	case msgEnter:
		if theLocker != nil {
			theLocker.doEnter()
		}
		return 0
	case msgExit:
		if theLocker != nil {
			theLocker.doExit()
		}
		return 0
	case msgSetHotkey:
		// Exécuté sur le thread worker : RegisterHotKey EXIGE le thread
		// propriétaire de la fenêtre.
		pUnregisterHotKey.Call(hwnd, hotkeyID)
		ok := true
		if wparam == 1 {
			mods := uint32(lparam>>16) & 0xFFFF
			vk := uint32(lparam) & 0xFFFF
			r, _, _ := pRegisterHotKey.Call(hwnd, hotkeyID, uintptr(mods), uintptr(vk))
			ok = r != 0
		}
		select {
		case hkResult <- ok:
		default:
		}
		return 0
	case wmHotkey:
		if theApp != nil {
			theApp.hotkeyLock()
		}
		return 0
	case msgReassert:
		// Garde la fenêtre de verrouillage au-dessus de tout + au premier plan.
		if theLocker != nil && theLocker.hwnd != 0 {
			pSetWindowPos.Call(theLocker.hwnd, hwndTopmost, 0, 0, 0, 0,
				swpNoMove|swpNoSize|swpNoActivate)
			fg, _, _ := pGetForegroundWindow.Call()
			if fg != theLocker.hwnd {
				pSetForegroundWindow.Call(theLocker.hwnd)
			}
		}
		return 0
	case msgTrayCallback:
		switch lparam & 0xFFFF {
		case wmRButtonUp:
			showTrayMenu(hwnd)
		case wmLButtonDblClk, wmLButtonUp:
			if theApp != nil {
				theApp.showWindow()
			}
		}
		return 0
	case wmCommand:
		switch wparam & 0xFFFF {
		case idOpen:
			if theApp != nil {
				theApp.showWindow()
			}
		case idLock:
			if theApp != nil {
				theApp.hotkeyLock()
			}
		case idQuit:
			if theApp != nil {
				theApp.quitApp()
			}
		}
		return 0
	case wmDestroy:
		pPostQuitMessage.Call(0)
		return 0
	}
	r, _, _ := pDefWindowProcW.Call(hwnd, umsg, wparam, lparam)
	return r
}

func (l *Locker) createWindow() {
	hInst, _, _ := pGetModuleHandleW.Call(0)
	cls := utf16Ptr("EnvLockMsgWindow")
	var wc wndClassEx
	wc.CbSize = uint32(unsafe.Sizeof(wc))
	wc.LpfnWndProc = wndProcPtr
	wc.HInstance = hInst
	wc.LpszClassName = cls
	pRegisterClassExW.Call(uintptr(unsafe.Pointer(&wc)))
	// Titre DISTINCT de la fenêtre Wails ("EnvLock") : sinon FindWindow peut
	// retrouver cette fenêtre cachée au lieu de la vraie -> le plein écran
	// s'appliquerait à une fenêtre invisible.
	h, _, _ := pCreateWindowExW.Call(
		0, uintptr(unsafe.Pointer(cls)),
		uintptr(unsafe.Pointer(utf16Ptr("EnvLockHiddenMsgWindow"))),
		0, 0, 0, 0, 0, 0, 0, hInst, 0,
	)
	l.msgHwnd = h
}

func loadAppIcon() uintptr {
	buf := make([]uint16, 512)
	pGetModuleFileNameW.Call(0, uintptr(unsafe.Pointer(&buf[0])), uintptr(len(buf)))
	hInst, _, _ := pGetModuleHandleW.Call(0)
	h, _, _ := pExtractIconW.Call(hInst, uintptr(unsafe.Pointer(&buf[0])), 0)
	if h > 1 {
		return h
	}
	h2, _, _ := pLoadIconW.Call(0, idiApplication)
	return h2
}

func (l *Locker) addTray() {
	var nid notifyIconData
	nid.CbSize = uint32(unsafe.Sizeof(nid))
	nid.HWnd = l.msgHwnd
	nid.UID = 1
	nid.UFlags = nifMessage | nifIcon | nifTip
	nid.UCallbackMessage = msgTrayCallback
	nid.HIcon = loadAppIcon()
	copyUTF16(nid.SzTip[:], l.tooltip)
	pShellNotifyIconW.Call(nimAdd, uintptr(unsafe.Pointer(&nid)))
}

func (l *Locker) removeTray() {
	var nid notifyIconData
	nid.CbSize = uint32(unsafe.Sizeof(nid))
	nid.HWnd = l.msgHwnd
	nid.UID = 1
	pShellNotifyIconW.Call(nimDelete, uintptr(unsafe.Pointer(&nid)))
}

func showTrayMenu(hwnd uintptr) {
	hmenu, _, _ := pCreatePopupMenu.Call()
	pAppendMenuW.Call(hmenu, mfString, idOpen, uintptr(unsafe.Pointer(utf16Ptr("Ouvrir le panneau"))))
	pAppendMenuW.Call(hmenu, mfString, idLock, uintptr(unsafe.Pointer(utf16Ptr("Verrouiller maintenant"))))
	pAppendMenuW.Call(hmenu, mfSeparator, 0, 0)
	pAppendMenuW.Call(hmenu, mfString, idQuit, uintptr(unsafe.Pointer(utf16Ptr("Quitter"))))
	var pt point
	pGetCursorPos.Call(uintptr(unsafe.Pointer(&pt)))
	pSetForegroundWindow.Call(hwnd)
	pTrackPopupMenu.Call(hmenu, tpmRight, uintptr(pt.X), uintptr(pt.Y), 0, hwnd, 0)
	pDestroyMenu.Call(hmenu)
}

// startWatch ré-affirme le premier plan/topmost pendant le verrouillage.
func (l *Locker) startWatch() {
	l.stopWatch = make(chan struct{})
	go func(stop chan struct{}, hwnd uintptr) {
		t := time.NewTicker(400 * time.Millisecond)
		defer t.Stop()
		for {
			select {
			case <-stop:
				return
			case <-t.C:
				pPostMessageW.Call(hwnd, msgReassert, 0, 0)
			}
		}
	}(l.stopWatch, l.msgHwnd)
}

func (l *Locker) stopWatchdog() {
	if l.stopWatch != nil {
		close(l.stopWatch)
		l.stopWatch = nil
	}
}

// ---- API utilisée par App -------------------------------------------
func (l *Locker) enter() {
	<-l.ready
	pPostMessageW.Call(l.msgHwnd, msgEnter, 0, 0)
}

func (l *Locker) exit() {
	<-l.ready
	pPostMessageW.Call(l.msgHwnd, msgExit, 0, 0)
}

func (l *Locker) applyHotkey(enabled bool, seq string) bool {
	<-l.ready
	var mods, vk uint32
	if enabled {
		var ok bool
		mods, vk, ok = parseHotkey(seq)
		if !ok {
			l.postSetHotkey(false, 0, 0) // au moins désenregistrer
			return false
		}
	}
	return l.postSetHotkey(enabled, mods, vk)
}

// postSetHotkey demande au thread worker d'(dé)enregistrer le raccourci et
// attend son résultat réel.
func (l *Locker) postSetHotkey(enabled bool, mods, vk uint32) bool {
	var en uintptr
	if enabled {
		en = 1
	}
	lp := uintptr(mods)<<16 | uintptr(vk)
	select { // vide un éventuel résultat périmé
	case <-hkResult:
	default:
	}
	pPostMessageW.Call(l.msgHwnd, msgSetHotkey, en, lp)
	select {
	case r := <-hkResult:
		return r
	case <-time.After(500 * time.Millisecond):
		return false
	}
}

func (l *Locker) shutdown() {
	pUnregisterHotKey.Call(l.msgHwnd, hotkeyID)
	l.removeTray()
}

func parseHotkey(seq string) (uint32, uint32, bool) {
	if strings.TrimSpace(seq) == "" {
		return 0, 0, false
	}
	var mods uint32 = modNoRepeat
	var vk uint32
	ok := false
	for _, part := range strings.Split(seq, "+") {
		p := strings.TrimSpace(part)
		switch strings.ToLower(p) {
		case "ctrl", "control":
			mods |= modControl
		case "alt":
			mods |= modAlt
		case "shift", "maj":
			mods |= modShift
		case "win", "meta", "cmd", "super":
			mods |= modWin
		default:
			if v, good := vkForKey(p); good {
				vk = v
				ok = true
			}
		}
	}
	return mods, vk, ok && vk != 0
}

func vkForKey(p string) (uint32, bool) {
	if len(p) == 1 {
		c := p[0]
		if c >= 'a' && c <= 'z' {
			c -= 32
		}
		if (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') {
			return uint32(c), true
		}
	}
	up := strings.ToUpper(p)
	if len(up) >= 2 && up[0] == 'F' {
		if n, err := strconv.Atoi(up[1:]); err == nil && n >= 1 && n <= 24 {
			return uint32(0x70 + n - 1), true
		}
	}
	switch up {
	case "SPACE":
		return 0x20, true
	case "ESC", "ESCAPE":
		return 0x1B, true
	}
	return 0, false
}
