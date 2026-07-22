package main

import (
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// logf ajoute une ligne horodatée à %APPDATA%\EnvLock\envlock.log.
// Diagnostic utile car l'app est en mode GUI (aucune console).
func logf(format string, args ...interface{}) {
	dir, err := os.UserConfigDir()
	if err != nil {
		dir, _ = os.UserHomeDir()
	}
	d := filepath.Join(dir, "EnvLock")
	_ = os.MkdirAll(d, 0o755)
	f, err := os.OpenFile(
		filepath.Join(d, "envlock.log"),
		os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644,
	)
	if err != nil {
		return
	}
	defer f.Close()
	fmt.Fprintf(f, "%s "+format+"\n",
		append([]interface{}{time.Now().Format("15:04:05")}, args...)...)
}
