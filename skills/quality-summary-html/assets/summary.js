(function(){
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function openUp(el){ for (var p = el; p; p = p.parentElement) if (p.tagName === 'DETAILS') p.open = true; }
  function flash(el){ el.classList.remove('hit'); void el.offsetWidth; el.classList.add('hit'); setTimeout(function(){ el.classList.remove('hit'); }, 3000); }
  function reveal(id, push){
    var el = document.getElementById(id);
    if (!el) return false;
    openUp(el);
    el.scrollIntoView({block: el.tagName === 'TR' ? 'center' : 'start', behavior: reduce ? 'auto' : 'smooth'});
    flash(el);
    if (push && location.hash !== '#' + id) history.pushState(null, '', '#' + id);
    return true;
  }
  function fromHash(){ if (location.hash.length > 1) reveal(decodeURIComponent(location.hash.slice(1)), false); }
  document.addEventListener('click', function(e){
    var a = e.target.closest('a[href^="#"]');
    if (!a) return;
    if (reveal(decodeURIComponent(a.getAttribute('href').slice(1)), true)) e.preventDefault();
  });
  window.addEventListener('popstate', fromHash);
  if (location.hash.length > 1) setTimeout(fromHash, 80);

  function setAll(open){ document.querySelectorAll('details.tbl').forEach(function(d){ d.open = open; }); }
  document.getElementById('open-all').addEventListener('click', function(){ setAll(true); });
  document.getElementById('close-all').addEventListener('click', function(){ setAll(false); });

  var tip = document.createElement('div');
  tip.className = 'tip'; tip.hidden = true; tip.setAttribute('role', 'tooltip');
  document.body.appendChild(tip);
  var cur = null;
  function show(el){
    var t = el.getAttribute('data-tip');
    if (!t) return;
    cur = el; tip.textContent = t; tip.hidden = false;
    var r = el.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    var x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
    var y = r.top - h - 8;
    if (y < 8) y = r.bottom + 8;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }
  function hide(){ cur = null; tip.hidden = true; }
  document.addEventListener('mouseover', function(e){
    var el = e.target.closest('[data-tip]');
    if (el === cur) return;
    if (el) show(el); else hide();
  });
  document.addEventListener('focusin', function(e){ var el = e.target.closest('[data-tip]'); if (el) show(el); });
  document.addEventListener('focusout', hide);
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') hide(); });
  window.addEventListener('scroll', hide, true);

  // 並べ替え: 1 回目は昇順（点は降順）、2 回目は逆、3 回目で元の順に戻す
  document.querySelectorAll('table[data-sortable]').forEach(function(t){
    var body = t.tBodies[0];
    var rows = Array.prototype.slice.call(body.rows);
    var heads = t.querySelectorAll('th[data-key]');
    heads.forEach(function(th){
      th.querySelector('button').addEventListener('click', function(){
        var key = th.getAttribute('data-key');
        var first = key === 'score' ? 'descending' : 'ascending';
        var second = first === 'ascending' ? 'descending' : 'ascending';
        var state = th.getAttribute('aria-sort');
        var next = state === 'none' ? first : state === first ? second : 'none';
        heads.forEach(function(o){ o.setAttribute('aria-sort', 'none'); });
        th.setAttribute('aria-sort', next);
        var sorted = rows.slice();
        if (next !== 'none') {
          var dir = next === 'ascending' ? 1 : -1;
          sorted.sort(function(a, b){
            return (Number(a.dataset[key]) - Number(b.dataset[key])) * dir || Number(a.dataset.i) - Number(b.dataset.i);
          });
        }
        sorted.forEach(function(r){ body.appendChild(r); });
      });
    });
  });
})();
