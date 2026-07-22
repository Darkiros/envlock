// UI : panneau <-> verrouillage, bindings Go, verrouillage multi-écran.
(function () {
  const $ = (id) => document.getElementById(id);
  let config = null, previewAnim = null, lockAnims = [], clockTimer = null;

  const App = () => window.go.main.App;
  function ready(cb) {
    if (window.go && window.go.main && window.go.main.App) return cb();
    setTimeout(() => ready(cb), 40);
  }
  const sphereOpts = () => (config && config.sphere ? config.sphere : {});

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
    const a = $("pw1").value, b = $("pw2").value, msg = $("pwMsg");
    if (a.length < 4) { msg.className = "msg err"; msg.textContent = "4 caractères minimum."; return; }
    if (a !== b) { msg.className = "msg err"; msg.textContent = "Les mots de passe diffèrent."; return; }
    await App().SetPassword(a);
    $("pw1").value = ""; $("pw2").value = "";
    msg.className = "msg ok"; msg.textContent = "Mot de passe enregistré.";
    refreshPassword();
  }

  function restartPreview() {
    if (previewAnim) previewAnim.stop();
    // Canvas neuf à chaque fois -> surface GPU propre (évite le crash du
    // renderer WebView2 quand on réutilise le canvas entre animations).
    const host = $("previewHost");
    host.innerHTML = "";
    const c = document.createElement("canvas");
    host.appendChild(c);
    previewAnim = createAnimation(config.animation, c, sphereOpts());
  }

  async function onAnimChange() {
    config.animation = $("animSelect").value;
    await App().SetAnimation(config.animation);
    restartPreview();
  }

  async function onClockChange() {
    config.clock = $("clockCheck").checked;
    await App().SetClock(config.clock);
  }

  // ---------- Verrouillage ----------
  function updateClock() {
    const now = new Date();
    $("clock").textContent = now.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
    $("date").textContent = now.toLocaleDateString("fr-FR",
      { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  }

  async function enterLock() {
    if ($("lock").classList.contains("active")) return; // déjà verrouillé
    if (!(await App().HasPassword())) { refreshPassword(); return; }

    // Un calque animé par moniteur + overlay (horloge/prompt) sur l'écran principal.
    const mons = await App().GetMonitors();
    const layers = $("layers");
    layers.innerHTML = "";
    lockAnims.forEach((a) => a.stop());
    lockAnims = [];
    let primary = mons.find((m) => m.primary) || mons[0] || { fx: 0, fy: 0, fw: 1, fh: 1 };

    mons.forEach((m) => {
      const c = document.createElement("canvas");
      c.style.left = m.fx * 100 + "%";
      c.style.top = m.fy * 100 + "%";
      c.style.width = m.fw * 100 + "%";
      c.style.height = m.fh * 100 + "%";
      layers.appendChild(c);
      lockAnims.push(createAnimation(config.animation, c, sphereOpts()));
    });

    const ov = $("primary");
    ov.style.left = primary.fx * 100 + "%";
    ov.style.top = primary.fy * 100 + "%";
    ov.style.width = primary.fw * 100 + "%";
    ov.style.height = primary.fh * 100 + "%";

    const showClock = config.clock !== false;
    $("clock").style.display = showClock ? "" : "none";
    $("date").style.display = showClock ? "" : "none";
    updateClock();
    clockTimer = setInterval(updateClock, 1000);

    showView("lock");
    await App().Lock(); // Go : plein écran multi-moniteur + hook clavier + anti-veille
    $("pwcard").classList.remove("show");
    setTimeout(() => window.focus(), 60);
  }

  async function tryUnlock() {
    if (await App().VerifyPassword($("unlockPw").value)) {
      await App().Unlock();
      cleanupLock();
      showView("panel");
      restartPreview();
    } else {
      $("unlockMsg").textContent = "Mot de passe incorrect";
      $("unlockPw").value = "";
    }
  }

  function cleanupLock() {
    lockAnims.forEach((a) => a.stop());
    lockAnims = [];
    if (clockTimer) { clearInterval(clockTimer); clockTimer = null; }
    $("pwcard").classList.remove("show");
    $("unlockPw").value = ""; $("unlockMsg").textContent = "";
  }

  function showPwCard() {
    $("unlockMsg").textContent = ""; $("unlockPw").value = "";
    $("pwcard").classList.add("show");
    $("unlockPw").focus();
  }

  function hkStatus(enabled, ok) {
    const m = $("hkMsg");
    if (!enabled) { m.className = "msg"; m.textContent = "Raccourci désactivé."; }
    else if (ok) { m.className = "msg ok"; m.textContent = "Raccourci actif : " + $("hkInput").value; }
    else { m.className = "msg err"; m.textContent = "Combinaison invalide ou déjà prise."; }
  }

  async function captureHotkey(e) {
    e.preventDefault();
    const parts = [];
    if (e.ctrlKey) parts.push("Ctrl");
    if (e.altKey) parts.push("Alt");
    if (e.shiftKey) parts.push("Shift");
    if (e.metaKey) parts.push("Win");
    const k = e.key;
    if (["Control", "Alt", "Shift", "Meta"].includes(k)) return;
    let key = null;
    if (k.length === 1 && /[a-zA-Z0-9]/.test(k)) key = k.toUpperCase();
    else if (/^F([1-9]|1[0-9]|2[0-4])$/.test(k)) key = k;
    else if (k === " " || k === "Spacebar") key = "Space";
    if (!key || parts.length === 0) return; // il faut au moins un modificateur
    const seq = [...parts, key].join("+");
    $("hkInput").value = seq;
    config.hotkey.sequence = seq;
    const ok = await App().SetHotkey($("hkCheck").checked, seq);
    hkStatus($("hkCheck").checked, ok);
  }

  // ---------- Événements ----------
  function wire() {
    $("min").onclick = () => window.runtime.WindowMinimise();
    $("close").onclick = () => {
      if (config.minimize_to_tray !== false) window.runtime.WindowHide();
      else window.runtime.Quit();
    };
    $("savePw").onclick = savePassword;
    $("animSelect").onchange = onAnimChange;
    $("clockCheck").onchange = onClockChange;
    $("lockBtn").onclick = enterLock;
    $("doUnlock").onclick = tryUnlock;
    $("cancelUnlock").onclick = () => $("pwcard").classList.remove("show");

    $("trayCheck").onchange = async () => {
      config.minimize_to_tray = $("trayCheck").checked;
      await App().SetMinimizeToTray(config.minimize_to_tray);
    };
    $("hkCheck").onchange = async () => {
      const en = $("hkCheck").checked;
      $("hkInput").disabled = !en;
      const ok = await App().SetHotkey(en, $("hkInput").value);
      hkStatus(en, ok);
    };
    $("hkInput").addEventListener("keydown", captureHotkey);

    window.runtime.EventsOn("trigger-lock", () => enterLock());

    document.addEventListener("keydown", (e) => {
      if (!$("lock").classList.contains("active")) return;
      const carte = $("pwcard").classList.contains("show");
      if (e.key === "Enter" && !carte) { showPwCard(); e.preventDefault(); }
      else if (e.key === "Enter" && carte) { tryUnlock(); e.preventDefault(); }
      else if (e.key === "Escape" && carte) { $("pwcard").classList.remove("show"); }
    });
  }

  ready(async () => {
    config = await App().GetConfig();
    if (!config.hotkey) config.hotkey = { enabled: true, sequence: "Ctrl+Alt+L" };
    $("animSelect").value = config.animation || "sphere";
    $("clockCheck").checked = config.clock !== false;
    $("trayCheck").checked = config.minimize_to_tray !== false;
    $("hkCheck").checked = !!config.hotkey.enabled;
    $("hkInput").value = config.hotkey.sequence || "";
    $("hkInput").disabled = !config.hotkey.enabled;
    hkStatus(config.hotkey.enabled, !!config.hotkey.enabled);
    wire();
    await refreshPassword();
    restartPreview();
  });
})();
