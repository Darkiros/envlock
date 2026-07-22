package main

import (
	"embed"
	"io/fs"

	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
	"github.com/wailsapp/wails/v2/pkg/options/windows"
)

//go:embed all:frontend/dist
var assets embed.FS

// assetsFS renvoie un FS où index.html est à la racine (Wails le cherche là).
func assetsFS() fs.FS {
	if _, err := assets.Open("index.html"); err == nil {
		return assets
	}
	if sub, err := fs.Sub(assets, "frontend/dist"); err == nil {
		logf("assets: racine via fs.Sub(frontend/dist)")
		return sub
	}
	logf("assets: fallback embed brut")
	return assets
}

// WindowTitle sert aussi de clé pour retrouver le HWND côté Win32.
const WindowTitle = "EnvLock"

func main() {
	logf("main: démarrage du process")
	app := NewApp()

	err := wails.Run(&options.App{
		Title:     WindowTitle,
		Width:     820,
		Height:    700,
		MinWidth:  520,
		MinHeight: 420,
		Frameless: true,
		AssetServer: &assetserver.Options{
			Assets: assetsFS(),
		},
		BackgroundColour: &options.RGBA{R: 5, G: 7, B: 13, A: 1},
		OnStartup:        app.startup,
		Bind:             []interface{}{app},
		Windows: &windows.Options{
			WebviewIsTransparent: false,
			WindowIsTranslucent:  false,
		},
	})
	if err != nil {
		logf("wails.Run erreur: %s", err.Error())
		println("Error:", err.Error())
	}
}
