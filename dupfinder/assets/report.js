(function () {
  var R = window.__REPORT__ || {};
  var KEY = "dupdec:" + (location.pathname || "report");
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card'));
  var groups = Array.prototype.slice.call(document.querySelectorAll('.group'));
  var containers = document.querySelectorAll('.cards');

  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) {}

  function setDecision(card, value) {
    card.dataset.decision = value;
    card.classList.toggle('d-move', value === 'move');
    card.classList.toggle('d-keep', value === 'keep');
    card.querySelectorAll('.decide button').forEach(function (b) {
      b.classList.toggle('on', b.dataset.set === value);
    });
  }

  function collect() {
    var d = {};
    cards.forEach(function (c) { d[c.dataset.path] = c.dataset.decision; });
    return d;
  }

  function payload() {
    return JSON.stringify({
      source: R.source, generated: R.generated, hash_distance: R.hash_distance,
      decisions: collect()
    }, null, 2);
  }

  function refresh() {
    try { localStorage.setItem(KEY, JSON.stringify(collect())); } catch (e) {}
    var move = 0, kept = 0, bad = false;
    groups.forEach(function (g) {
      var gc = Array.prototype.slice.call(g.querySelectorAll('.card'));
      var m = gc.filter(function (c) { return c.dataset.decision === 'move'; }).length;
      g.classList.toggle('invalid', m > 0 && m === gc.length);
      if (g.classList.contains('invalid')) bad = true;
      move += m;
      if (m === 0) kept++;
    });
    var c = document.getElementById('counter');
    c.textContent = move + ' to move · ' + kept + ' groups kept intact'
      + (bad ? ' · fix red groups' : '');
    c.classList.toggle('warn', bad);
  }

  cards.forEach(function (card) {
    setDecision(card, saved[card.dataset.path] || card.dataset.decision || 'keep');
    card.querySelectorAll('.decide button').forEach(function (b) {
      b.addEventListener('click', function () { setDecision(card, b.dataset.set); refresh(); });
    });
  });

  groups.forEach(function (g) {
    g.querySelectorAll('[data-g]').forEach(function (b) {
      b.addEventListener('click', function () {
        g.querySelectorAll('.card').forEach(function (c) {
          if (b.dataset.g === 'keepall') setDecision(c, 'keep');
          else setDecision(c, c.classList.contains('keep') ? 'keep' : 'move');
        });
        refresh();
      });
    });
  });

  var layout = document.getElementById('layout');
  layout.addEventListener('change', function () {
    var col = layout.value === 'col';
    containers.forEach(function (c) { c.classList.toggle('col', col); c.classList.toggle('row', !col); });
  });
  document.querySelectorAll('[data-thumb]').forEach(function (b) {
    b.addEventListener('click', function () {
      document.documentElement.style.setProperty('--thumb', b.dataset.thumb + 'px');
    });
  });

  document.getElementById('download').addEventListener('click', function () {
    var blob = new Blob([payload()], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = '_duplicate_decisions.json';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  });

  document.getElementById('copy').addEventListener('click', function () {
    var text = payload(), btn = this, old = btn.textContent;
    if (navigator.clipboard) { navigator.clipboard.writeText(text); }
    else {
      var ta = document.createElement('textarea');
      ta.value = text; document.body.appendChild(ta); ta.select();
      document.execCommand('copy'); ta.remove();
    }
    btn.textContent = 'Copied'; setTimeout(function () { btn.textContent = old; }, 1200);
  });

  refresh();
})();
