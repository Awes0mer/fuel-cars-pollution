/* Interactive, animated flowcharts for the Fuel, Cars & Pollution site.
   Plain JavaScript, no external code. All numbers come from the JSON block
   #flow-data, which the site build writes from results/learning_results.json. */
(function () {
  'use strict';
  var dataEl = document.getElementById('flow-data');
  if (!dataEl) return;
  var D = JSON.parse(dataEl.textContent);
  var SVGNS = 'http://www.w3.org/2000/svg';
  var reduceMotion = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  var LINKS = [
    { key: 'Crude->Gasoline', src: 'Crude', dst: 'Gasoline' },
    { key: 'Gasoline->FuelUse', src: 'Gasoline', dst: 'FuelUse' },
    { key: 'VMT->FuelUse', src: 'VMT', dst: 'FuelUse' },
    { key: 'EVShare->FuelUse', src: 'EVShare', dst: 'FuelUse' },
    { key: 'FuelUse->CO2', src: 'FuelUse', dst: 'CO2' }
  ];
  var uid = 0;

  function weightOf(w, key) { return w[key.split('->')[1]][key]; }
  function svgEl(name, attrs) {
    var e = document.createElementNS(SVGNS, name);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }
  function signed(v, digits) {
    var d = digits === undefined ? 1 : digits;
    var r = Number(v.toFixed(d));
    if (r === 0) return '0.' + '0'.repeat(d);
    return (r > 0 ? '+' : '−') + Math.abs(r).toFixed(d);
  }
  function dirOf(v, eps) { return Math.abs(v) < (eps || 0.005) ? 'flat' : (v > 0 ? 'up' : 'down'); }

  // ---------- one flow graph: nodes are HTML, wires are an SVG overlay ----------
  function Graph(stage) {
    var self = this;
    this.stage = stage;
    this.svg = stage.querySelector('svg.flow-wires');
    this.visible = true;
    this.nodes = {};
    Array.prototype.forEach.call(stage.querySelectorAll('.fnode'), function (el) { self.nodes[el.getAttribute('data-node')] = el; });
    var id = 'fx' + (uid++);
    var defs = svgEl('defs', {});
    ['flat', 'up', 'down'].forEach(function (k) {
      var m = svgEl('marker', { id: id + '-' + k, viewBox: '0 0 10 10', refX: '8', refY: '5', markerUnits: 'userSpaceOnUse', markerWidth: '13', markerHeight: '13', orient: 'auto-start-reverse' });
      m.appendChild(svgEl('path', { d: 'M0,0 L10,5 L0,10 z', 'class': 'mk mk-' + k }));
      defs.appendChild(m);
    });
    this.svg.appendChild(defs);
    this.markerId = id;
    this.links = LINKS.map(function (def) {
      var gEl = svgEl('g', { 'class': 'link' });
      var bg = svgEl('path', { 'class': 'wire-bg' });
      var path = svgEl('path', { 'class': 'wire flat', 'marker-end': 'url(#' + id + '-flat)' });
      var dots = svgEl('g', { 'class': 'dots' });
      var label = svgEl('text', { 'class': 'wire-label', 'text-anchor': 'middle' });
      gEl.appendChild(bg); gEl.appendChild(path); gEl.appendChild(dots); gEl.appendChild(label);
      self.svg.appendChild(gEl);
      return { def: def, g: gEl, bg: bg, path: path, dotsG: dots, label: label, dots: [], phase: Math.random(), len: 1, w: 0, contrib: 0, dir: 'flat' };
    });
    this.byKey = {};
    this.links.forEach(function (L) { self.byKey[L.def.key] = L; });
    this.layout();
    var t = null;
    var relayout = function () { clearTimeout(t); t = setTimeout(function () { self.layout(); }, 60); };
    window.addEventListener('resize', relayout);
    if ('ResizeObserver' in window) new ResizeObserver(relayout).observe(stage);
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) { self.visible = es[0].isIntersecting; }).observe(stage);
    }
  }

  Graph.prototype.rect = function (el) {
    var b = this.stage.getBoundingClientRect(), r = el.getBoundingClientRect();
    return { l: r.left - b.left, r: r.right - b.left, t: r.top - b.top, b: r.bottom - b.top, cx: (r.left + r.right) / 2 - b.left, cy: (r.top + r.bottom) / 2 - b.top };
  };

  Graph.prototype.layout = function () {
    var self = this;
    var box = this.stage.getBoundingClientRect();
    if (!box.width) return;
    this.svg.setAttribute('viewBox', '0 0 ' + box.width + ' ' + box.height);
    this.links.forEach(function (L) {
      var s = self.rect(self.nodes[L.def.src]), t = self.rect(self.nodes[L.def.dst]), d, x1, y1, x2, y2, m;
      if (t.l >= s.r - 2) { // target to the right: horizontal wire
        x1 = s.r; y1 = s.cy; x2 = t.l - 4; y2 = t.cy; m = (x1 + x2) / 2;
        d = 'M' + x1 + ',' + y1 + ' C' + m + ',' + y1 + ' ' + m + ',' + y2 + ' ' + x2 + ',' + y2;
      } else { // target below: vertical wire
        x1 = s.cx; y1 = s.b; x2 = t.cx; y2 = t.t - 4; m = (y1 + y2) / 2;
        d = 'M' + x1 + ',' + y1 + ' C' + x1 + ',' + m + ' ' + x2 + ',' + m + ' ' + x2 + ',' + y2;
      }
      L.path.setAttribute('d', d);
      L.bg.setAttribute('d', d);
      L.len = L.path.getTotalLength() || 1;
      var p = L.path.getPointAtLength(L.len * 0.5);
      L.label.setAttribute('x', p.x);
      L.label.setAttribute('y', p.y - 9);
    });
    this.place();
  };

  Graph.prototype.setWeight = function (key, w) {
    var L = this.byKey[key];
    L.w = w;
    L.path.style.strokeWidth = (2 + 9 * Math.min(1, Math.abs(w) / 1.3)).toFixed(2) + 'px';
    L.label.textContent = '×' + (Number(w.toFixed(2)) < 0 ? '−' : '') + Math.abs(w).toFixed(2);
  };

  // contrib = weight x source change: how hard this link pushes its target, and which way.
  Graph.prototype.setFlow = function (key, contrib) {
    var L = this.byKey[key];
    L.contrib = contrib;
    var dir = dirOf(contrib, 0.01);
    L.dir = dir;
    L.path.setAttribute('class', 'wire ' + dir);
    L.path.setAttribute('marker-end', 'url(#' + this.markerId + '-' + dir + ')');
    var n = 0;
    if (!reduceMotion && dir !== 'flat') n = Math.min(7, 1 + Math.floor(1.6 * Math.log(1 + Math.abs(contrib)) / Math.LN2 / 1.5));
    while (L.dots.length < n) {
      var c = svgEl('circle', { r: '4.5' });
      L.dotsG.appendChild(c);
      L.dots.push(c);
    }
    while (L.dots.length > n) L.dotsG.removeChild(L.dots.pop());
    L.dotsG.setAttribute('class', 'dots ' + dir);
    this.place();
  };

  Graph.prototype.setNode = function (name, value, unit, sub) {
    var el = this.nodes[name];
    if (!el) return;
    var v = el.querySelector('.val');
    var before = v.textContent;
    var dir = value === null || value === undefined ? 'flat' : dirOf(value);
    v.textContent = value === null || value === undefined ? 'missing' : signed(value, unit === 'pts' || Math.abs(value) < 1 ? 2 : 1) + (unit === 'pts' ? ' pts' : '%');
    var arrow = el.querySelector('.arr');
    if (arrow) arrow.textContent = dir === 'up' ? '▲' : dir === 'down' ? '▼' : '●';
    el.classList.remove('up', 'down', 'flat');
    el.classList.add(dir);
    var s = el.querySelector('.sub');
    if (s) s.textContent = sub || '';
    if (!reduceMotion && v.textContent !== before) {
      el.classList.remove('flash');
      void el.offsetWidth;
      el.classList.add('flash');
    }
  };

  Graph.prototype.place = function () {
    this.links.forEach(function (L) {
      var n = L.dots.length;
      for (var i = 0; i < n; i++) {
        var p = (L.phase + i / n) % 1;
        var pt = L.path.getPointAtLength(p * L.len);
        L.dots[i].setAttribute('cx', pt.x.toFixed(1));
        L.dots[i].setAttribute('cy', pt.y.toFixed(1));
        L.dots[i].setAttribute('opacity', Math.min(1, p * 6, (1 - p) * 6).toFixed(2));
      }
    });
  };

  Graph.prototype.tick = function (dt) {
    this.links.forEach(function (L) {
      if (L.dots.length) L.phase = (L.phase + dt * 0.085 / L.len) % 1;
    });
    this.place();
  };

  var graphs = [];
  var last = 0;
  function frame(ts) {
    var dt = last ? Math.min(64, ts - last) : 16;
    last = ts;
    if (!document.hidden) graphs.forEach(function (g) { if (g.visible) g.tick(dt); });
    requestAnimationFrame(frame);
  }

  // ---------- 1. price-shock flow ----------
  function initShock() {
    var root = document.getElementById('shock-flow');
    if (!root) return;
    var g = new Graph(root.querySelector('.flow-stage'));
    graphs.push(g);
    var W = D.weights;
    LINKS.forEach(function (l) { g.setWeight(l.key, weightOf(W, l.key)); });
    var inp = { crude: root.querySelector('#fx-crude'), vmt: root.querySelector('#fx-vmt'), ev: root.querySelector('#fx-ev') };
    var out = { crude: root.querySelector('#fx-crude-v'), vmt: root.querySelector('#fx-vmt-v'), ev: root.querySelector('#fx-ev-v') };
    var summary = root.querySelector('.flow-summary');
    var timers = [];
    function later(ms, fn) { if (ms <= 0) fn(); else timers.push(setTimeout(fn, ms)); }

    function run(stagger) {
      timers.forEach(clearTimeout);
      timers = [];
      var c = +inp.crude.value, m = +inp.vmt.value, e = +inp.ev.value;
      out.crude.textContent = signed(c, 0) + '%';
      out.vmt.textContent = signed(m, 1) + '%';
      out.ev.textContent = signed(e, 1) + ' pts';
      var wCG = weightOf(W, 'Crude->Gasoline'), wGF = weightOf(W, 'Gasoline->FuelUse'), wVF = weightOf(W, 'VMT->FuelUse'),
          wEF = weightOf(W, 'EVShare->FuelUse'), wFC = weightOf(W, 'FuelUse->CO2');
      var gas = wCG * c;
      var pGas = wGF * gas, pVmt = wVF * m, pEv = wEF * e;
      var fuel = pGas + pVmt + pEv;
      var co2 = wFC * fuel;
      var step = stagger && !reduceMotion ? 700 : 0;
      g.setNode('Crude', c, '%');
      g.setNode('VMT', m, '%');
      g.setNode('EVShare', e, 'pts');
      g.setFlow('Crude->Gasoline', wCG * c);
      g.setFlow('VMT->FuelUse', pVmt);
      g.setFlow('EVShare->FuelUse', pEv);
      if (step) {
        g.setFlow('Gasoline->FuelUse', 0);
        g.setFlow('FuelUse->CO2', 0);
      }
      later(step, function () { g.setNode('Gasoline', gas, '%'); g.setFlow('Gasoline->FuelUse', pGas); });
      later(step * 2, function () { g.setNode('FuelUse', fuel, '%'); g.setFlow('FuelUse->CO2', co2); });
      later(step * 3, function () {
        g.setNode('CO2', co2, '%');
        var parts = [['gasoline price', pGas], ['miles driven', pVmt], ['EV share', pEv]];
        parts.sort(function (a, b) { return Math.abs(b[1]) - Math.abs(a[1]); });
        var big = Math.abs(parts[0][1]) < 0.005 ? '' : ' The biggest push on gasoline burned comes from ' + parts[0][0] + ' (' + signed(parts[0][1], 2) + ' points).';
        summary.textContent = 'Crude oil ' + signed(c, 0) + '% → gasoline price ' + signed(gas, 1) + '% (×' + wCG.toFixed(2) +
          ') → gasoline burned ' + signed(fuel, 2) + '% → transport CO2 ' + signed(co2, 2) + '% (×' + wFC.toFixed(2) + ').' + big;
      });
    }
    Object.keys(inp).forEach(function (k) { inp[k].addEventListener('input', function () { run(false); }); });
    Array.prototype.forEach.call(root.querySelectorAll('[data-preset]'), function (b) {
      b.addEventListener('click', function () {
        var p = b.getAttribute('data-preset').split(',');
        inp.crude.value = p[0]; inp.vmt.value = p[1]; inp.ev.value = p[2];
        run(true);
      });
    });
    run(false);
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (es) {
        if (es[0].isIntersecting) { io.disconnect(); run(true); }
      }, { threshold: 0.4 });
      io.observe(root);
    }
  }

  // ---------- 2. learning replay ----------
  function initReplay() {
    var root = document.getElementById('learn-flow');
    if (!root) return;
    var g = new Graph(root.querySelector('.flow-stage'));
    graphs.push(g);
    var Y = D.years, H = D.history;
    var zero = { Gasoline: { 'Crude->Gasoline': 0 }, FuelUse: { 'Gasoline->FuelUse': 0, 'VMT->FuelUse': 0, 'EVShare->FuelUse': 0 }, CO2: { 'FuelUse->CO2': 0 } };
    function before(year) { return H[String(year - 1)] || zero; }
    function after(year) { return H[String(year)] || before(year); }
    var slider = root.querySelector('#lr-year');
    slider.max = String(Y.length - 1);
    var playBtn = root.querySelector('#lr-play');
    var steps = root.querySelectorAll('.step');
    var f = {};
    ['year', 'period', 'pred', 'actual', 'err', 'nc', 'knn', 'note'].forEach(function (k) { f[k] = root.querySelector('[data-f="' + k + '"]'); });
    var strip = root.querySelector('svg.err-strip');
    var bars = buildStrip(strip, Y, function (i) { stop(); show(i, true); });
    var idx = 0, playing = false, timers = [];
    function later(ms, fn) { timers.push(setTimeout(fn, ms)); }
    function clear() { timers.forEach(clearTimeout); timers = []; }
    function stage(n) { Array.prototype.forEach.call(steps, function (s, i) { s.classList.toggle('on', i === n); }); }
    function setWeights(w) { LINKS.forEach(function (l) { g.setWeight(l.key, weightOf(w, l.key)); }); }

    function show(i, animate) {
      clear();
      idx = i;
      slider.value = String(i);
      var y = Y[i];
      bars.forEach(function (b, j) { b.classList.toggle('cur', j === i); });
      f.year.textContent = y.year;
      f.period.textContent = y.period === 'holdout' ? 'holdout (scored for the verdict)' : y.period === 'design' ? 'design (used to pick settings)' : 'burn-in (not scored)';
      var wb = before(y.year);
      var inputs = y.inputs;
      var step = animate && !reduceMotion ? 520 : 0;
      // 1. predict with last year's weights
      stage(0);
      setWeights(wb);
      g.setNode('Crude', inputs.Crude, '%');
      g.setNode('Gasoline', inputs.Gasoline, '%');
      g.setNode('VMT', inputs.VMT, '%');
      g.setNode('EVShare', inputs.EVShare, 'pts', inputs.EVShare === null ? 'no data yet' : '');
      g.setNode('FuelUse', y.pred_fuel, '%', 'predicted');
      g.setNode('CO2', y.pred, '%', 'predicted');
      LINKS.forEach(function (l) {
        var src = l.src === 'FuelUse' ? y.pred_fuel : inputs[l.src];
        g.setFlow(l.key, src === null ? 0 : weightOf(wb, l.key) * src);
      });
      f.pred.textContent = signed(y.pred, 2) + '%';
      f.actual.textContent = '…';
      f.err.textContent = '…';
      f.nc.textContent = '…';
      f.knn.textContent = '…';
      f.note.textContent = y.note || '';
      var compare = function () {
        stage(1);
        g.setNode('FuelUse', y.actual_fuel, '%', 'actual (predicted ' + signed(y.pred_fuel, 1) + '%)');
        g.setNode('CO2', y.actual, '%', 'actual (predicted ' + signed(y.pred, 1) + '%)');
        f.actual.textContent = y.actual === null ? 'missing' : signed(y.actual, 2) + '%';
        f.err.textContent = y.actual === null ? 'n/a' : Math.abs(y.pred - y.actual).toFixed(2) + ' pts';
        f.nc.textContent = y.actual === null ? 'n/a' : Math.abs(y.actual).toFixed(2) + ' pts';
        f.knn.textContent = y.actual === null || y.knn === null ? 'n/a' : Math.abs(y.knn - y.actual).toFixed(2) + ' pts';
      };
      var refit = function () { stage(2); setWeights(after(y.year)); };
      var store = function () { stage(3); };
      if (!step) { compare(); refit(); store(); return; }
      later(step, compare);
      later(step * 2, refit);
      later(step * 3, store);
      if (playing) later(step * 4 + 250, function () {
        if (idx < Y.length - 1) show(idx + 1, true); else stop();
      });
    }
    function play() {
      playing = true;
      playBtn.textContent = 'Pause';
      playBtn.setAttribute('aria-pressed', 'true');
      show(idx >= Y.length - 1 ? 0 : idx + 1, true);
    }
    function stop() {
      playing = false;
      playBtn.textContent = 'Play';
      playBtn.setAttribute('aria-pressed', 'false');
    }
    playBtn.addEventListener('click', function () { if (playing) { stop(); clear(); show(idx, false); } else play(); });
    slider.addEventListener('input', function () { stop(); show(+slider.value, false); });
    root.querySelector('#lr-prev').addEventListener('click', function () { stop(); show(Math.max(0, idx - 1), true); });
    root.querySelector('#lr-next').addEventListener('click', function () { stop(); show(Math.min(Y.length - 1, idx + 1), true); });
    var start = 0;
    for (var i = 0; i < Y.length; i++) if (Y[i].year === D.start_year) start = i;
    show(start, false);
  }

  // error strip: one bar per predicted year, height = |graph error|; dot = |no-change error|
  function buildStrip(svg, Y, onPick) {
    var W = 640, Hh = 120, L = 6, R = 6, T = 10, B = 22;
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + Hh);
    var y0 = Y[0].year, y1 = Y[Y.length - 1].year;
    var cap = 8;
    var bw = (W - L - R) / (y1 - y0 + 1);
    function X(yr) { return L + (yr - y0) * bw; }
    function Hs(v) { return (Hh - T - B) * Math.min(cap, v) / cap; }
    var hx = X(D.holdout_start);
    svg.appendChild(svgEl('rect', { x: hx, y: T, width: W - R - hx, height: Hh - T - B, 'class': 'band' }));
    var lab = svgEl('text', { x: hx + 4, y: T + 12, 'class': 'band-label' });
    lab.textContent = 'holdout';
    svg.appendChild(lab);
    var bars = [];
    Y.forEach(function (y, i) {
      var e = y.actual === null ? 0 : Math.abs(y.pred - y.actual);
      var r = svgEl('rect', { x: X(y.year) + 1, y: Hh - B - Hs(e), width: Math.max(1, bw - 2), height: Math.max(1, Hs(e)), 'class': 'bar' });
      var t = svgEl('title', {});
      t.textContent = y.year + ': graph error ' + e.toFixed(2) + ' pts' + (y.actual === null ? '' : ', no-change error ' + Math.abs(y.actual).toFixed(2));
      r.appendChild(t);
      r.addEventListener('click', function () { onPick(i); });
      svg.appendChild(r);
      if (y.actual !== null) {
        svg.appendChild(svgEl('circle', { cx: X(y.year) + bw / 2, cy: Hh - B - Hs(Math.abs(y.actual)), r: 2.6, 'class': 'nc-dot' }));
      }
      if (y.year % 10 === 0) {
        var tx = svgEl('text', { x: X(y.year) + bw / 2, y: Hh - 6, 'class': 'yr', 'text-anchor': 'middle' });
        tx.textContent = y.year;
        svg.appendChild(tx);
      }
      bars.push(r);
    });
    return bars;
  }

  initShock();
  initReplay();
  if (graphs.length && !reduceMotion) requestAnimationFrame(frame);
})();
