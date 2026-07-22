// Logique UI : panneau <-> écran verrouillé, appels aux bindings Go.
(function () {
  const $ = (id) => document.getElementById(id);
  let config = null, lockOrb = null, previewOrb = null, clockTimer = null;

  // Attend l'injection des bindings Wails (window.go).
  function ready(cb) {
    if (window.go && window.go.main && window.go.main.App) return cb();
    setTimeout(() => ready(cb), 40);
  }

  function App() { return window.go.main.App; }

  function showView(id) {
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    $(id).classList.add("active");
  }

  // ---------- Panneau ----------
  async function refreshPassword() {
    const has = await App().HasPassword();
    $("pwStatus").innerHTML = has
      ? "<b>✔ Un mot de passe est défini.</b>"
      : "⚠ Aucun mot de passe — obligatoire avant de verrouiller.";
    $("lockBtn").disabled = !has;
    $("lockMsg").textContent = has ? "" : "Définis d'abord un mot de passe.";
  }

  async function savePassword() {
    const a = $("pw1").value, b = $("pw2").value;
    const msg = $("pwMsg");
    if (a.length < 4) { msg.className = "msg err"; msg.textContent = "4 caractères minimum."; return; }
    if (a !== b) { msg.className = "msg err"; msg.textContent = "Les mots de passe diffèrent."; return; }
    await App().SetPassword(a);
    $("pw1").value = ""; $("pw2").value = "";
    msg.className = "msg ok"; msg.textContent = "Mot de passe enregistré.";
    refreshPassword();
  }

  // ---------- Verrouillage ----------
  function updateClock() {
    const now = new Date();
    $("clock").textContent = now.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
    $("date").textContent = now.toLocaleDateString("fr-FR",
      { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  }

  async function enterLock() {
    if (!(await App().HasPassword())) { refreshPassword(); return; }
    showView("lock");
    // Affiche/masque l'horloge selon la config.
    $("clock").style.display = config && config.clock === false ? "none" : "";
    $("date").style.display = config && config.clock === false ? "none" : "";
    updateClock();
    clockTimer = setInterval(updateClock, 1000);
    lockOrb = startOrb($("lockCanvas"), config ? config.sphere : null);
    // Bloque l'environnement côté Go (fenêtre plein écran + hook + anti-veille).
    await App().Lock();
    $("pwcard").classList.remove("show");
    setTimeout(() => window.focus(), 50);
  }

  async function tryUnlock() {
    const ok = await App().VerifyPassword($("unlockPw").value);
    if (ok) {
      await App().Unlock();
      cleanupLock();
      showView("panel");
    } else {
      $("unlockMsg").textContent = "Mot de passe incorrect";
      $("unlockPw").value = "";
    }
  }

  function cleanupLock() {
    if (lockOrb) { lockOrb.stop(); lockOrb = null; }
    if (clockTimer) { clearInterval(clockTimer); clockTimer = null; }
    $("pwcard").classList.remove("show");
    $("unlockPw").value = "";
    $("unlockMsg").textContent = "";
  }

  function showPwCard() {
    $("unlockMsg").textContent = "";
    $("unlockPw").value = "";
    $("pwcard").classList.add("show");
    $("unlockPw").focus();
  }

  // ---------- Événements ----------
  function wire() {
    $("min").onclick = () => window.runtime.WindowMinimise();
    $("close").onclick = () => window.runtime.Quit();
    $("savePw").onclick = savePassword;
    $("lockBtn").onclick = enterLock;
    $("doUnlock").onclick = tryUnlock;
    $("cancelUnlock").onclick = () => $("pwcard").classList.remove("show");

    document.addEventListener("keydown", (e) => {
      if (!$("lock").classList.contains("active")) return;
      const carte = $("pwcard").classList.contains("show");
      if ((e.key === "Enter") && !carte) { showPwCard(); e.preventDefault(); }
      else if (e.key === "Enter" && carte) { tryUnlock(); e.preventDefault(); }
      else if (e.key === "Escape" && carte) { $("pwcard").classList.remove("show"); }
    });
  }

  ready(async () => {
    config = await App().GetConfig();
    wire();
    await refreshPassword();
    previewOrb = startOrb($("previewCanvas"), config.sphere);
  });
})();
