package main

import (
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"

	"golang.org/x/crypto/pbkdf2"
)

// Password : hash PBKDF2-HMAC-SHA256 + sel (jamais de mot de passe en clair).
type Password struct {
	Algo string `json:"algo"`
	Iter int    `json:"iterations"`
	Salt string `json:"salt"`
	Hash string `json:"hash"`
}

type Hotkey struct {
	Enabled  bool   `json:"enabled"`
	Sequence string `json:"sequence"`
}

type Config struct {
	Animation      string             `json:"animation"`
	Clock          bool               `json:"clock"`
	Hotkey         Hotkey             `json:"hotkey"`
	MinimizeToTray bool               `json:"minimize_to_tray"`
	Sphere         map[string]float64 `json:"sphere"`
	Password       *Password          `json:"password"`
}

func defaultConfig() Config {
	return Config{
		Animation:      "sphere",
		Clock:          true,
		Hotkey:         Hotkey{Enabled: true, Sequence: "Ctrl+Alt+L"},
		MinimizeToTray: true,
		Sphere: map[string]float64{
			"count": 800, "amp": 0.20, "wave_speed": 1.0, "rot_speed": 0.35,
			"dot_size": 1.7, "hue": 193, "pulse": 0.15,
		},
	}
}

func configPath() string {
	dir, err := os.UserConfigDir()
	if err != nil {
		dir, _ = os.UserHomeDir()
	}
	d := filepath.Join(dir, "EnvLock")
	_ = os.MkdirAll(d, 0o755)
	return filepath.Join(d, "config.json")
}

func loadConfig() Config {
	c := defaultConfig()
	if b, err := os.ReadFile(configPath()); err == nil {
		_ = json.Unmarshal(b, &c)
	}
	return c
}

func (c Config) save() error {
	b, _ := json.MarshalIndent(c, "", "  ")
	return os.WriteFile(configPath(), b, 0o644)
}

func hashPassword(pw string) *Password {
	salt := make([]byte, 16)
	_, _ = rand.Read(salt)
	iter := 200_000
	dk := pbkdf2.Key([]byte(pw), salt, iter, 32, sha256.New)
	return &Password{
		Algo: "pbkdf2_sha256", Iter: iter,
		Salt: hex.EncodeToString(salt), Hash: hex.EncodeToString(dk),
	}
}

func (p *Password) verify(pw string) bool {
	if p == nil {
		return false
	}
	salt, err := hex.DecodeString(p.Salt)
	if err != nil {
		return false
	}
	want, err := hex.DecodeString(p.Hash)
	if err != nil {
		return false
	}
	dk := pbkdf2.Key([]byte(pw), salt, p.Iter, len(want), sha256.New)
	return subtle.ConstantTimeCompare(dk, want) == 1
}
