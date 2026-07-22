//go:build windows

package main

import (
	"runtime"
	"syscall"
	"time"
	"unsafe"
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
	pSetThreadExecutionSt = kernel32.NewProc("SetThreadExecutionState")
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

type command int

const (
	cmdEnter command = iota
	cmdExit
)

// Locker : toute l'intégration Win32 tourne sur une goroutine dédiée avec
// une boucle de messages (nécessaire pour le hook bas niveau).
type Locker struct {
	cmds chan command
	hwnd uintptr
	prev rect
	hook uintptr
}

func newLocker() *Locker {
	l := &Locker{cmds: make(chan command, 8)}
	go l.worker()
	return l
}

func (l *Locker) enter() { l.cmds <- cmdEnter }
func (l *Locker) exit()  { l.cmds <- cmdExit }

func (l *Locker) worker() {
	runtime.LockOSThread()
	ticker := time.NewTicker(5 * time.Millisecond)
	defer ticker.Stop()
	var m msg
	for {
		select {
		case c := <-l.cmds:
			switch c {
			case cmdEnter:
				l.doEnter()
			case cmdExit:
				l.doExit()
			}
		case <-ticker.C:
		}
		// Pompe les messages -> le hook clavier peut se déclencher.
		for {
			r, _, _ := pPeekMessageW.Call(
				uintptr(unsafe.Pointer(&m)), 0, 0, 0, pmRemove,
			)
			if r == 0 {
				break
			}
			pTranslateMessage.Call(uintptr(unsafe.Pointer(&m)))
			pDispatchMessageW.Call(uintptr(unsafe.Pointer(&m)))
		}
	}
}

func metric(i int) int32 {
	r, _, _ := pGetSystemMetrics.Call(uintptr(i))
	return int32(r)
}

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
}

func (l *Locker) doExit() {
	if l.hook != 0 {
		pUnhookWindowsHookEx.Call(l.hook)
		l.hook = 0
	}
	if l.hwnd != 0 {
		w := l.prev.Right - l.prev.Left
		h := l.prev.Bottom - l.prev.Top
		pSetWindowPos.Call(l.hwnd, hwndNoTopmost,
			uintptr(l.prev.Left), uintptr(l.prev.Top),
			uintptr(w), uintptr(h), swpShowWindow)
	}
	pSetThreadExecutionSt.Call(esContinuous)
}
