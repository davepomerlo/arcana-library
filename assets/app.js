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
    var run = function () {
      var v = norm(q.value.trim()); var terms = v ? v.split(/\s+/) : [];
      if (!terms.length) { res.innerHTML = ""; cnt.textContent = ""; return; }
      loadIndex(function (d) {
        var hits = [];
        d.forEach(function (e) {
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
          hits.push([sc, e]);
        });
        hits.sort(function (a, b) { return b[0] - a[0]; });
        cnt.textContent = hits.length + " result" + (hits.length === 1 ? "" : "s");
        res.innerHTML = hits.slice(0, 80).map(function (h) {
          var e = h[1], ext = e.k === "library";
          var href = ext ? e.u : root + e.u;
          return '<li><a href="' + escH(href) + '"' + (ext ? ' rel="noopener"' : "") + ">" + escH(e.t) + "</a> " +
            (e.o ? '<span class="muted">' + escH(e.o) + "</span> " : "") +
            '<span class="badge">' + (ext ? "library" : "archive") + "</span> " +
            '<span class="muted">' + escH(e.x) + '</span><br><span class="snip">' + snippet(e, terms) + "</span></li>";
        }).join("");
      });
    };
    var t0; q.addEventListener("input", function () { clearTimeout(t0); t0 = setTimeout(run, 120); });
    var p = new URLSearchParams(location.search).get("q"); if (p) { q.value = p; run(); }
  }
  var rnd = document.getElementById("random-text");
  if (rnd) rnd.addEventListener("click", function (ev) {
    ev.preventDefault();
    loadIndex(function (d) {
      var a = d.filter(function (e) { return e.k === "archive"; });
      if (a.length) location.href = root + a[Math.floor(Math.random() * a.length)].u;
    });
  });
})();
