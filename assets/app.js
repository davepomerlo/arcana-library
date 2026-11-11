(function () {
  "use strict";
  var root = document.body.getAttribute("data-root") || "";
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

  // mobile menu
  var mb = document.querySelector(".menu-btn"), nav = document.getElementById("nav");
  if (mb && nav) mb.addEventListener("click", function () {
    var open = nav.classList.toggle("open"); mb.setAttribute("aria-expanded", open ? "true" : "false");
  });

  // theme
  var tb = document.querySelector(".theme-btn");
  if (tb) tb.addEventListener("click", function () {
    var cur = document.documentElement.dataset.theme ||
      (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    var next = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next; store("arc-theme", next);
  });

  // reading view (side by side / translation / original / romanization)
  var vc = document.querySelector(".view-ctl");
  if (vc) {
    var setView = function (v) {
      document.body.classList.remove("view-both", "view-trans", "view-orig");
      document.body.classList.add("view-" + v);
      vc.querySelectorAll("[data-view]").forEach(function (b) { b.setAttribute("aria-pressed", b.dataset.view === v ? "true" : "false"); });
      store("arc-view", v);
    };
    vc.querySelectorAll("[data-view]").forEach(function (b) { b.addEventListener("click", function () { setView(b.dataset.view); }); });
    var saved = store("arc-view"); if (saved) setView(saved);
    var rb = vc.querySelector("[data-roman]");
    if (rb) {
      var setRoman = function (on) { document.body.classList.toggle("show-roman", on); rb.setAttribute("aria-pressed", on ? "true" : "false"); store("arc-roman", on ? "1" : "0"); };
      rb.addEventListener("click", function () { setRoman(!document.body.classList.contains("show-roman")); });
      setRoman(store("arc-roman") === "1");
    }
  }

  // text normalisation for search/filter: lowercase, strip accents
  function norm(s) { return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""); }

  // section filter buttons + text filter (library and timeline)
  var fb = document.querySelector(".filter-b");
  var lq = document.getElementById("lib-q");
  var current = "";
  function applyFilter() {
    var q = lq ? norm(lq.value.trim()) : "";
    var terms = q ? q.split(/\s+/) : [];
    var shown = 0;
    document.querySelectorAll(".lib .work, .tl .timeline li").forEach(function (li) {
      var sec = li.getAttribute("data-sec") || (li.closest(".lib-sec") ? li.closest(".lib-sec").getAttribute("data-sec") : "");
      var hay = norm(li.getAttribute("data-hay") || li.textContent);
      var ok = (!current || sec === current || sec === "libraries" && !current) && terms.every(function (t) { return hay.indexOf(t) >= 0; });
      if (current && sec === "libraries") ok = false;
      li.classList.toggle("hide", !ok); if (ok) shown++;
    });
    document.querySelectorAll(".lib-sec").forEach(function (s) {
      s.classList.toggle("hide", !s.querySelector(".work:not(.hide)"));
    });
    var c = document.getElementById("lib-count"); if (c) c.textContent = shown + " shown";
  }
  if (fb) fb.querySelectorAll("button").forEach(function (b) {
    b.addEventListener("click", function () {
      current = b.dataset.filter;
      fb.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      applyFilter();
    });
  });
  if (lq) { lq.addEventListener("input", applyFilter); applyFilter(); }

  // search index (search page + random text)
  var idx = null;
  function loadIndex(cb) {
    if (idx) return cb(idx);
    fetch(root + "search-index.json").then(function (r) { return r.json(); }).then(function (d) {
      d.forEach(function (e) { e._t = norm(e.t + " " + e.o); e._g = norm(e.g + " " + e.x); e._s = norm(e.s); e._b = norm(e.b); });
      idx = d; cb(d);
    }).catch(function () { var c = document.getElementById("q-count"); if (c) c.textContent = "Search needs the site to be served over http (it works on GitHub Pages)."; });
  }
  function escH(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function snippet(e, terms) {
    var src = e.b || e.s; var n = norm(src); var pos = -1;
    for (var i = 0; i < terms.length && pos < 0; i++) pos = n.indexOf(terms[i]);
    if (pos < 0) return escH(e.s.slice(0, 200));
    var a = Math.max(0, pos - 80), out = escH((a ? "…" : "") + src.slice(a, pos + 160) + "…");
    terms.forEach(function (t) {
      if (t.length < 2 && !/[^\x00-\x7f]/.test(t)) return;
      out = out.replace(new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi"), "<mark>$1</mark>");
    });
    return out;
  }
  var q = document.getElementById("q");
  if (q) {
    var res = document.getElementById("results"), cnt = document.getElementById("q-count");
    var F = { sec: "f-sec", lang: "f-lang", area: "f-area", era: "f-era", theme: "f-theme", st: "f-st", kind: "f-kind" };
    var fv = function (k) { var el = document.getElementById(F[k]); return el ? el.value : ""; };
    var anyFilter = function () { return Object.keys(F).some(function (k) { return fv(k); }); };
    var passes = function (e) {
      if (fv("sec") && e.sc !== fv("sec")) return false;
      if (fv("kind") && e.k !== fv("kind")) return false;
      if (fv("lang") && e.l !== fv("lang")) return false;
      if (fv("area") && e.a !== fv("area")) return false;
      if (fv("st") && e.st !== fv("st")) return false;
      if (fv("theme") && (e.th || []).indexOf(fv("theme")) < 0) return false;
      if (fv("era")) {
        if (e.y === null || e.y === undefined) return false;
        var r = fv("era").split(":"); if (e.y < +r[0] || e.y > +r[1]) return false;
      }
      return true;
    };
    var syncUrl = function () {
      var p = new URLSearchParams();
      if (q.value.trim()) p.set("q", q.value.trim());
      Object.keys(F).forEach(function (k) { if (fv(k)) p.set(k, fv(k)); });
      var s = p.toString(); history.replaceState(null, "", location.pathname + (s ? "?" + s : ""));
    };
    var run = function () {
      var v = norm(q.value.trim()); var terms = v ? v.split(/\s+/) : [];
      syncUrl();
      if (!terms.length && !anyFilter()) { res.innerHTML = ""; cnt.textContent = ""; return; }
      loadIndex(function (d) {
        var hits = [];
        d.forEach(function (e) {
          if (!passes(e)) return;
          var sc = 0;
          for (var i = 0; i < terms.length; i++) {
            var t = terms[i], s = 0;
            if (e._t.indexOf(t) >= 0) s += 10;
            if (e._g.indexOf(t) >= 0) s += 5;
            if (e._s.indexOf(t) >= 0) s += 3;
            if (e._b.indexOf(t) >= 0) s += 1;
            if (!s) return; sc += s;
          }
          if (e.k === "archive") sc += 2;
          if (!terms.length) sc = -(e.y === null || e.y === undefined ? 99999 : e.y);
          hits.push([sc, e]);
        });
        hits.sort(function (a, b) { return b[0] - a[0]; });
        cnt.textContent = hits.length + " result" + (hits.length === 1 ? "" : "s");
        res.innerHTML = hits.slice(0, 120).map(function (h) {
          var e = h[1], ext = e.k === "library";
          var href = ext ? e.u : root + e.u;
          return '<li><a href="' + escH(href) + '"' + (ext ? ' rel="noopener"' : "") + ">" + escH(e.t) + "</a> " +
            (e.o ? '<span class="muted">' + escH(e.o) + "</span> " : "") +
            '<span class="badge">' + (ext ? "library" : "archive") + "</span> " +
            '<span class="muted">' + escH(e.x) + (e.l ? " · " + escH(e.l) : "") + '</span><br><span class="snip">' + snippet(e, terms) + "</span></li>";
        }).join("");
      });
    };
    var t0; q.addEventListener("input", function () { clearTimeout(t0); t0 = setTimeout(run, 120); });
    Object.keys(F).forEach(function (k) { var el = document.getElementById(F[k]); if (el) el.addEventListener("change", run); });
    var clr = document.getElementById("f-clear");
    if (clr) clr.addEventListener("click", function () { Object.keys(F).forEach(function (k) { var el = document.getElementById(F[k]); if (el) el.value = ""; }); run(); });
    var params = new URLSearchParams(location.search), opened = false;
    Object.keys(F).forEach(function (k) { var v = params.get(k); var el = document.getElementById(F[k]); if (v && el) { el.value = v; opened = true; } });
    if (opened) { var fd = document.getElementById("filters"); if (fd) fd.open = true; }
    var p0 = params.get("q"); if (p0) q.value = p0;
    if (p0 || opened) run();
  }
  var rnd = document.getElementById("random-text");
  if (rnd) rnd.addEventListener("click", function (ev) {
    ev.preventDefault();
    loadIndex(function (d) {
      var a = d.filter(function (e) { return e.k === "archive"; });
      if (a.length) location.href = root + a[Math.floor(Math.random() * a.length)].u;
    });
  });

  // ---------------------------------------------------------------- shelf: saved texts and reading progress
  function getJ(k) { try { return JSON.parse(store(k) || "{}") || {}; } catch (e) { return {}; } }
  function setJ(k, v) { store(k, JSON.stringify(v)); }
  var art = document.querySelector("article.text[data-slug]");
  var saveBtn = document.querySelector("[data-save]");
  if (saveBtn) {
    var slug = saveBtn.dataset.slug;
    var paint = function () { var on = !!getJ("arc-shelf")[slug]; saveBtn.textContent = on ? "★ Saved" : "☆ Save to shelf"; saveBtn.setAttribute("aria-pressed", on ? "true" : "false"); };
    saveBtn.addEventListener("click", function () {
      var sh = getJ("arc-shelf");
      if (sh[slug]) delete sh[slug]; else sh[slug] = { title: saveBtn.dataset.title, at: Date.now() };
      setJ("arc-shelf", sh); paint();
    });
    paint();
  }
  if (art) {
    var aslug = art.dataset.slug, atitle = art.dataset.title, tick = null;
    var pr = getJ("arc-progress")[aslug];
    if (pr && pr.p > 0.08 && pr.p < 0.97) {
      var tb = document.querySelector(".tools-bar");
      if (tb) {
        var rb2 = document.createElement("button"); rb2.type = "button";
        rb2.textContent = "↓ Resume (" + Math.round(pr.p * 100) + "%)";
        rb2.addEventListener("click", function () { window.scrollTo({ top: pr.p * (document.documentElement.scrollHeight - innerHeight), behavior: "smooth" }); });
        tb.appendChild(rb2);
      }
    }
    window.addEventListener("scroll", function () {
      if (tick) return;
      tick = setTimeout(function () {
        tick = null;
        var max = document.documentElement.scrollHeight - innerHeight; if (max <= 0) return;
        var p = Math.min(1, Math.max(0, scrollY / max));
        var all = getJ("arc-progress"); var old = all[aslug] || { p: 0 };
        all[aslug] = { title: atitle, p: p, max: Math.max(old.max || 0, p), at: Date.now() };
        setJ("arc-progress", all);
      }, 600);
    }, { passive: true });
  }
  var ss = document.getElementById("shelf-saved");
  if (ss) {
    var renderShelf = function () {
      var sh = getJ("arc-shelf"), pg = getJ("arc-progress");
      var keys = Object.keys(sh).sort(function (a, b) { return sh[b].at - sh[a].at; });
      ss.innerHTML = keys.length ? keys.map(function (k) {
        var p = pg[k] ? Math.round((pg[k].max || pg[k].p) * 100) : 0;
        return '<li class="work"><a href="' + root + "texts/" + escH(k) + '.html">' + escH(sh[k].title) + '</a><span class="w-meta">saved ' + new Date(sh[k].at).toLocaleDateString() + ' · read ' + p + '%</span><span class="bar"><span style="width:' + p + '%"></span></span></li>';
      }).join("") : '<li class="muted">Nothing saved yet. Use “☆ Save to shelf” on any text.</li>';
      var sp = document.getElementById("shelf-progress");
      var pk = Object.keys(pg).sort(function (a, b) { return pg[b].at - pg[a].at; }).slice(0, 40);
      sp.innerHTML = pk.length ? pk.map(function (k) {
        var p = Math.round((pg[k].max || pg[k].p) * 100);
        return '<li class="work"><a href="' + root + "texts/" + escH(k) + '.html">' + escH(pg[k].title) + '</a><span class="w-meta">last read ' + new Date(pg[k].at).toLocaleDateString() + ' · ' + p + '%</span><span class="bar"><span style="width:' + p + '%"></span></span></li>';
      }).join("") : '<li class="muted">No reading progress yet.</li>';
    };
    renderShelf();
    document.getElementById("shelf-clear").addEventListener("click", function () {
      if (confirm("Remove all saved texts and reading progress from this browser?")) { store("arc-shelf", "{}"); store("arc-progress", "{}"); renderShelf(); }
    });
    document.getElementById("shelf-export").addEventListener("click", function () {
      var blob = new Blob([JSON.stringify({ shelf: getJ("arc-shelf"), progress: getJ("arc-progress") }, null, 1)], { type: "application/json" });
      var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "arcana-shelf.json"; a.click();
    });
  }

  // ---------------------------------------------------------------- read aloud (device text-to-speech)
  var readBtn = document.querySelector("[data-read]");
  if (readBtn) {
    if (!("speechSynthesis" in window)) { readBtn.hidden = true; }
    else {
      var reading = false;
      var stopRead = function () { speechSynthesis.cancel(); reading = false; readBtn.textContent = "▶ Read aloud"; readBtn.setAttribute("aria-pressed", "false"); document.querySelectorAll(".speaking").forEach(function (x) { x.classList.remove("speaking"); }); };
      readBtn.addEventListener("click", function () {
        if (reading) return stopRead();
        var parts = Array.prototype.slice.call(document.querySelectorAll(".text-body .par-t"));
        if (!parts.length) parts = Array.prototype.slice.call(document.querySelectorAll(".text-body p, .text-body li, .text-body h2"));
        if (!parts.length) return;
        reading = true; readBtn.textContent = "■ Stop reading"; readBtn.setAttribute("aria-pressed", "true");
        var i = 0;
        var next = function () {
          document.querySelectorAll(".speaking").forEach(function (x) { x.classList.remove("speaking"); });
          if (!reading || i >= parts.length) return stopRead();
          var el = parts[i++]; el.classList.add("speaking"); el.scrollIntoView({ block: "center", behavior: "smooth" });
          var u = new SpeechSynthesisUtterance(el.innerText); u.lang = el.getAttribute("lang") || "en"; u.rate = 0.95;
          u.onend = next; u.onerror = next; speechSynthesis.speak(u);
        };
        next();
      });
      window.addEventListener("pagehide", stopRead);
    }
  }

  // ---------------------------------------------------------------- map: time slider and filters
  var my = document.getElementById("map-year");
  if (my) {
    var out = document.getElementById("map-year-out"), msec = document.getElementById("map-sec"), mth = document.getElementById("map-theme");
    var mp = new URLSearchParams(location.search); if (mp.get("theme")) mth.value = mp.get("theme");
    var fmt = function (y) { y = +y; return y < 0 ? (-y) + " BCE" : y + " CE"; };
    var applyMap = function () {
      var y = +my.value, s = msec.value, th = mth.value, n = 0;
      out.textContent = fmt(y);
      document.querySelectorAll(".pin, .map-row").forEach(function (el) {
        var ok = +el.dataset.y <= y && (!s || el.dataset.sec === s) && (!th || (" " + el.dataset.th + " ").indexOf(" " + th + " ") >= 0);
        el.classList.toggle("hide", !ok); if (ok && el.classList.contains("pin")) n++;
      });
      document.getElementById("map-count").textContent = n + " texts shown";
    };
    [my, msec, mth].forEach(function (el) { el.addEventListener("input", applyMap); el.addEventListener("change", applyMap); });
    var play = document.getElementById("map-play"), timer = null;
    play.addEventListener("click", function () {
      if (timer) { clearInterval(timer); timer = null; play.textContent = "▶ Play through history"; play.setAttribute("aria-pressed", "false"); return; }
      my.value = my.min; play.textContent = "■ Stop"; play.setAttribute("aria-pressed", "true");
      timer = setInterval(function () {
        var v = +my.value + Math.max(20, Math.round((+my.max - +my.min) / 120));
        if (v >= +my.max) { v = +my.max; clearInterval(timer); timer = null; play.textContent = "▶ Play through history"; play.setAttribute("aria-pressed", "false"); }
        my.value = v; applyMap();
      }, 120);
    });
    applyMap();
  }

  // ---------------------------------------------------------------- installable app: service worker and offline status
  var ns = document.getElementById("net-status");
  var showNet = function () { if (!ns) return; ns.hidden = navigator.onLine; ns.textContent = navigator.onLine ? "" : "You are offline — reading from the copy stored on this device."; };
  window.addEventListener("online", showNet); window.addEventListener("offline", showNet); showNet();
  var okSW = "serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost");
  if (okSW) {
    try {
      navigator.serviceWorker.register(root + "sw.js").then(function () {
        var os = document.getElementById("offline-state");
        if (os && navigator.serviceWorker.controller) {
          navigator.serviceWorker.addEventListener("message", function (ev) {
            if (ev.data && ev.data.type === "progress") os.textContent = "Stored for offline reading: " + ev.data.cached + " of " + ev.data.total + " files.";
          });
          navigator.serviceWorker.controller.postMessage("progress");
        }
      }).catch(function () {});
    } catch (e) {}
  } else {
    var os2 = document.getElementById("offline-state"); if (os2) os2.textContent = "Offline storage is available on the published site (https).";
  }
})();
