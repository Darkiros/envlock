//go:build windows

package main

import (
	"syscall"
	"unsafe"

	"golang.org/x/sys/windows/registry"
)

var (
	user32   = syscall.NewLazyDLL("user32.dll")
	kernel32 = syscall.NewLazyDLL("kernel32.dll")

	pFindWindowW          = user32.NewProc("FindWindowW")
	pGetWindowRect        = user32.NewProc("GetWindowRect")
	pSetWindowPos         = user32.NewProc("SetWindowPos")
	pGetSystemMetrics     = user32.NewProc("GetSystemMetrics")
	pSetWindowsHookExW    = user32.NewProc("SetWindowsHookExW")
	pCallNextHookEx       = user32.NewProc("CallNextHookEx")
	pUnhookWindowsHookEx  = user32.NewProc("UnhookWindowsHookEx")
	pGetAsyncKeyState     = user32.NewProc("GetAsyncKeyState")
	pPeekMessageW         = user32.NewProc("PeekMessageW")
	pTranslateMessage     = user32.NewProc("TranslateMessage")
	pDispatchMessageW     = user32.NewProc("DispatchMessageW")
	pEnumDisplayMonitors  = user32.NewProc("EnumDisplayMonitors")
	pGetMonitorInfoW      = user32.NewProc("GetMonitorInfoW")
	pGetWindowThreadPID   = user32.NewProc("GetWindowThreadProcessId")
	pAttachThreadInput    = user32.NewProc("AttachThreadInput")
	pBringWindowToTop     = user32.NewProc("BringWindowToTop")
	pSetFocus             = user32.NewProc("SetFocus")
	pGetWindow            = user32.NewProc("GetWindow")
	pShowWindow           = user32.NewProc("ShowWindow")
	pSetThreadExecutionSt = kernel32.NewProc("SetThreadExecutionState")
	pGetCurrentThreadId   = kernel32.NewProc("GetCurrentThreadId")
)

const (
	swHide     = 0
	swMinimize = 6
	swRestore  = 9
)

const (
	whKeyboardLL = 13
	hcAction     = 0
	pmRemove     = 0x0001

	swpShowWindow = 0x0040
	smXVirtual    = 76
	smYVirtual    = 77
	smCXVirtual   = 78
	smCYVirtual   = 79

	esContinuous      = 0x80000000
	esSystemRequired  = 0x00000001
	esDisplayRequired = 0x00000002

	llkhfAltDown = 0x20

	vkTab     = 0x09
	vkEscape  = 0x1B
	vkSpace   = 0x20
	vkLWin    = 0x5B
	vkRWin    = 0x5C
	vkApps    = 0x5D
	vkF4      = 0x73
	vkControl = 0x11
	vkShift   = 0x10
)

var (
	hwndTopmost   = ^uintptr(0) // (HWND)-1
	hwndNoTopmost = ^uintptr(1) // (HWND)-2
)

type rect struct{ Left, Top, Right, Bottom int32 }

type point struct{ X, Y int32 }

type msg struct {
	Hwnd    uintptr
	Message uint32
	WParam  uintptr
	LParam  uintptr
	Time    uint32
	Pt      point
}

type kbdllhookstruct struct {
	VkCode      uint32
	ScanCode    uint32
	Flags       uint32
	Time        uint32
	DwExtraInfo uintptr
}

func isDown(vk int) bool {
	r, _, _ := pGetAsyncKeyState.Call(uintptr(vk))
	return r&0x8000 != 0
}

func shouldBlock(kb *kbdllhookstruct) bool {
	vk := kb.VkCode
	alt := kb.Flags&llkhfAltDown != 0
	ctrl := isDown(vkControl)
	shift := isDown(vkShift)

	switch {
	case vk == vkLWin || vk == vkRWin: // touche Windows
		return true
	case vk == vkApps: // menu contextuel
		return true
	case vk == vkTab && (alt || ctrl): // Alt+Tab / Ctrl+Tab
		return true
	case vk == vkEscape && (alt || ctrl): // Alt/Ctrl+Échap
		return true
	case vk == vkF4 && alt: // Alt+F4
		return true
	case vk == vkSpace && alt: // Alt+Espace
		return true
	case vk == vkEscape && ctrl && shift: // Ctrl+Maj+Échap
		return true
	}
	return false
}

// Le hook doit être un callback global maintenu vivant.
var hookProcPtr = syscall.NewCallback(func(nCode, wParam, lParam uintptr) uintptr {
	if nCode == hcAction {
		kb := (*kbdllhookstruct)(unsafe.Pointer(lParam))
		if shouldBlock(kb) {
			return 1 // avale la frappe
		}
	}
	r, _, _ := pCallNextHookEx.Call(0, nCode, wParam, lParam)
	return r
})

func metric(i int) int32 {
	r, _, _ := pGetSystemMetrics.Call(uintptr(i))
	return int32(r)
}

// forceFocus donne réellement le focus clavier à la fenêtre ET à son enfant
// WebView. Sans ça, il faut cliquer avant que les frappes soient reçues.
// AttachThreadInput est nécessaire pour que SetFocus/SetForegroundWindow
// aboutissent depuis un autre thread que celui de la fenêtre.
func forceFocus(hwnd uintptr) {
	if hwnd == 0 {
		return
	}
	target, _, _ := pGetWindowThreadPID.Call(hwnd, 0)
	cur, _, _ := pGetCurrentThreadId.Call()
	attached := false
	if target != cur {
		r, _, _ := pAttachThreadInput.Call(cur, target, 1)
		attached = r != 0
	}
	pBringWindowToTop.Call(hwnd)
	pSetForegroundWindow.Call(hwnd)
	pSetFocus.Call(hwnd)
	if child, _, _ := pGetWindow.Call(hwnd, 5 /* GW_CHILD */); child != 0 {
		pSetFocus.Call(child)
	}
	if attached {
		pAttachThreadInput.Call(cur, target, 0)
	}
}

// captureForeground renvoie la fenêtre actuellement au premier plan (à mémoriser
// avant de verrouiller, pour y revenir au déverrouillage).
func captureForeground() uintptr {
	r, _, _ := pGetForegroundWindow.Call()
	return r
}

// restoreForeground redonne le premier plan à une fenêtre donnée.
func restoreForeground(hwnd uintptr) {
	if hwnd == 0 {
		return
	}
	target, _, _ := pGetWindowThreadPID.Call(hwnd, 0)
	cur, _, _ := pGetCurrentThreadId.Call()
	attached := false
	if target != cur {
		r, _, _ := pAttachThreadInput.Call(cur, target, 1)
		attached = r != 0
	}
	pBringWindowToTop.Call(hwnd)
	pSetForegroundWindow.Call(hwnd)
	if attached {
		pAttachThreadInput.Call(cur, target, 0)
	}
}

// setTaskMgrDisabled (dés)active le Gestionnaire des tâches via la policy
// per-utilisateur (HKCU, sans droits admin). Ferme la voie de kill la plus
// courante depuis l'écran Ctrl+Alt+Suppr. Réversible.
func setTaskMgrDisabled(disabled bool) {
	k, _, err := registry.CreateKey(
		registry.CURRENT_USER,
		`Software\Microsoft\Windows\CurrentVersion\Policies\System`,
		registry.SET_VALUE,
	)
	if err != nil {
		logf("DisableTaskMgr: CreateKey err=%v", err)
		return
	}
	defer k.Close()
	v := uint32(0)
	if disabled {
		v = 1
	}
	if err := k.SetDWordValue("DisableTaskMgr", v); err != nil {
		logf("DisableTaskMgr: SetDWordValue(%d) err=%v", v, err)
	} else {
		logf("DisableTaskMgr = %d (ok)", v)
	}
}

// cleanupKillGuards restaure les policies (au démarrage, au cas où l'app aurait
// été tuée en état verrouillé).
func cleanupKillGuards() { setTaskMgrDisabled(false) }

type monitorInfo struct {
	CbSize    uint32
	RcMonitor rect
	RcWork    rect
	DwFlags   uint32
}

// Accumulateur pour EnumDisplayMonitors (appel synchrone -> pas de course).
var enumRects []rect
var enumPrimary []bool

var monEnumProc = syscall.NewCallback(func(hMon, hdc, lprc, data uintptr) uintptr {
	var mi monitorInfo
	mi.CbSize = uint32(unsafe.Sizeof(mi))
	if r, _, _ := pGetMonitorInfoW.Call(hMon, uintptr(unsafe.Pointer(&mi))); r != 0 {
		enumRects = append(enumRects, mi.RcMonitor)
		enumPrimary = append(enumPrimary, mi.DwFlags&0x1 != 0) // MONITORINFOF_PRIMARY
	}
	return 1 // continuer l'énumération
})

func monitorFractions() []MonitorFrac {
	vx, vy := float64(metric(smXVirtual)), float64(metric(smYVirtual))
	vw, vh := float64(metric(smCXVirtual)), float64(metric(smCYVirtual))
	if vw <= 0 || vh <= 0 {
		return []MonitorFrac{{Fx: 0, Fy: 0, Fw: 1, Fh: 1, Primary: true}}
	}
	enumRects = nil
	enumPrimary = nil
	pEnumDisplayMonitors.Call(0, 0, monEnumProc, 0)
	out := make([]MonitorFrac, 0, len(enumRects))
	for i, r := range enumRects {
		out = append(out, MonitorFrac{
			Fx:      (float64(r.Left) - vx) / vw,
			Fy:      (float64(r.Top) - vy) / vh,
			Fw:      float64(r.Right-r.Left) / vw,
			Fh:      float64(r.Bottom-r.Top) / vh,
			Primary: enumPrimary[i],
		})
	}
	if len(out) == 0 {
		out = append(out, MonitorFrac{Fx: 0, Fy: 0, Fw: 1, Fh: 1, Primary: true})
	}
	return out
}

func (l *Locker) doEnter() {
	if l.hwnd == 0 {
		title, _ := syscall.UTF16PtrFromString(WindowTitle)
		r, _, _ := pFindWindowW.Call(0, uintptr(unsafe.Pointer(title)))
		l.hwnd = r
	}
	if l.hwnd != 0 {
		// Restaure (dé-cache tray / dé-minimise) AVANT de mesurer et d'agrandir.
		// Fait en Win32 sur ce thread -> pas de course avec des appels Wails.
		pShowWindow.Call(l.hwnd, swRestore)
		pGetWindowRect.Call(l.hwnd, uintptr(unsafe.Pointer(&l.prev)))
		vx, vy := metric(smXVirtual), metric(smYVirtual)
		vw, vh := metric(smCXVirtual), metric(smCYVirtual)
		pSetWindowPos.Call(l.hwnd, hwndTopmost,
			uintptr(vx), uintptr(vy), uintptr(vw), uintptr(vh), swpShowWindow)
	}
	if l.hook == 0 {
		h, _, _ := pSetWindowsHookExW.Call(whKeyboardLL, hookProcPtr, 0, 0)
		l.hook = h
	}
	pSetThreadExecutionSt.Call(esContinuous | esSystemRequired | esDisplayRequired)
	setTaskMgrDisabled(true)
	forceFocus(l.hwnd) // focus clavier immédiat (sinon il faut cliquer)
	l.startWatch()
}

func (l *Locker) doExit() {
	l.stopWatchdog()
	setTaskMgrDisabled(false)
	if l.hook != 0 {
		pUnhookWindowsHookEx.Call(l.hook)
		l.hook = 0
	}
	if l.hwnd != 0 {
		w := l.prev.Right - l.prev.Left
		h := l.prev.Bottom - l.prev.Top
		// Sans SWP_NOACTIVATE ici : c'est Unlock() (côté Go/Wails) qui décide de
		// l'état final (panneau devant / minimisé / tray) juste après.
		pSetWindowPos.Call(l.hwnd, hwndNoTopmost,
			uintptr(l.prev.Left), uintptr(l.prev.Top),
			uintptr(w), uintptr(h), swpShowWindow|swpNoActivate)
	}
	pSetThreadExecutionSt.Call(esContinuous)
	// État final déterministe (Win32, ce thread).
	switch l.exitMode {
	case exitHide:
		pShowWindow.Call(l.hwnd, swHide)
	case exitMinimize:
		pShowWindow.Call(l.hwnd, swMinimize)
	}
	if l.exitMode == exitPanel {
		forceFocus(l.hwnd) // panneau devant + focus
	} else if l.fgRestore != 0 {
		restoreForeground(l.fgRestore) // rendre le premier plan à l'appli d'avant
	}
	if l.exitDone != nil {
		close(l.exitDone)
	}
}

// selfWindow renvoie le handle de la fenêtre principale Wails (titre "EnvLock").
func selfWindow() uintptr {
	title, _ := syscall.UTF16PtrFromString(WindowTitle)
	r, _, _ := pFindWindowW.Call(0, uintptr(unsafe.Pointer(title)))
	return r
}

// bringToForeground redonne le premier plan à une fenêtre (appli d'avant le lock).
func bringToForeground(hwnd uintptr) { restoreForeground(hwnd) }
