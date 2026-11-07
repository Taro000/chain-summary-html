// design-summary-html: additions to base.js (a copy of quality-summary-html's summary.js)
(function(){
  var MERMAID_URL = '__MERMAID_URL__';
  // the page's wording for the messages below (assets/lang/<lang>.json, keys starting with js_)
  var UI = {};
  try { UI = JSON.parse(document.getElementById('ui-text').textContent); } catch (e) {}

  // ID tooltips are looked up in the JSON block at the end of the page, instead of repeating each text thousands of times
  var TIPS = {};
  try { TIPS = JSON.parse(document.getElementById('id-tips').textContent); } catch (e) {}
  function addTip(e){
    var el = e.target.closest && e.target.closest('.id');
    if (!el || el.hasAttribute('data-tip')) return;
    var ref = el.getAttribute('data-ref') || el.textContent.trim();
    if (TIPS[ref]) el.setAttribute('data-tip', TIPS[ref]);
  }
  document.addEventListener('mouseover', addTip, true);
  document.addEventListener('focusin', addTip, true);

  // "Open all" and "Close all" also open and close the nested toggles
  function setItems(open){ document.querySelectorAll('details.item').forEach(function(d){ d.open = open; }); }
  document.getElementById('open-all').addEventListener('click', function(){ setItems(true); });
  document.getElementById('close-all').addEventListener('click', function(){ setItems(false); });

  // Mermaid diagrams are rendered when they come into view, never while their toggle is closed
  var loading = null;
  function loadMermaid(){
    if (!loading) {
      loading = import(MERMAID_URL).then(function(m){
        var mermaid = m.default;
        var cs = getComputedStyle(document.documentElement);
        var v = function(n){ return cs.getPropertyValue(n).trim(); };
        // Diagrams are drawn in the page's neutrals: white boxes outlined in ink, groups and notes in the paper color.
        // The accent appears in a diagram only as a link (the threat model's flow numbers) and its highlight
        mermaid.initialize({
          startOnLoad: false, securityLevel: 'strict', suppressErrorRendering: true, theme: 'base',
          fontFamily: v('--f-body'),
          themeVariables: {
            fontFamily: v('--f-body'), fontSize: '13px',
            primaryColor: v('--surface'), primaryBorderColor: v('--ink-3'), primaryTextColor: v('--ink'),
            secondaryColor: v('--head'), secondaryBorderColor: v('--rule'), tertiaryColor: v('--surface'),
            tertiaryBorderColor: v('--rule'), lineColor: v('--ink-3'), textColor: v('--ink'),
            mainBkg: v('--surface'), nodeBorder: v('--ink-3'), clusterBkg: v('--paper'), clusterBorder: v('--rule'),
            titleColor: v('--ink'), edgeLabelBackground: v('--surface'),
            actorBkg: v('--surface'), actorBorder: v('--ink-3'), actorTextColor: v('--ink'), actorLineColor: v('--rule'),
            signalColor: v('--ink-2'), signalTextColor: v('--ink'), labelBoxBkgColor: v('--head'),
            labelBoxBorderColor: v('--rule'), labelTextColor: v('--ink'), loopTextColor: v('--ink-2'),
            noteBkgColor: v('--paper'), noteBorderColor: v('--rule'), noteTextColor: v('--ink'),
            activationBkgColor: v('--head'), activationBorderColor: v('--ink-3'), sequenceNumberColor: v('--surface'),
            attributeBackgroundColorOdd: v('--surface'), attributeBackgroundColorEven: v('--head')
          },
          flowchart: { useMaxWidth: false, htmlLabels: true, wrappingWidth: 240, padding: 10 },
          // the script has already broken the text at punctuation; measuring and drawing with the same font keeps labels off the arrows
          sequence: { useMaxWidth: false, mirrorActors: false, wrap: false, width: 140, actorMargin: 36,
            messageMargin: 34, boxMargin: 8, noteMargin: 8, messageFontSize: 13, noteFontSize: 12, actorFontSize: 13,
            messageFontFamily: v('--f-body'), noteFontFamily: v('--f-body'), actorFontFamily: v('--f-body') },
          state: { useMaxWidth: false },
          er: { useMaxWidth: false }
        });
        return mermaid;
      });
    }
    return loading;
  }

  // Direction: a flowchart or ER diagram too wide for the column is also drawn the other way (LR <-> TB), and the
  // drawing that shows larger in the column is kept. The diagram's content does not change
  function flipped(src, kind){
    var lines = src.split('\n'), k = 0;
    while (k < lines.length && !lines[k].trim()) k++;
    if (kind === 'erDiagram') {
      for (var i = k + 1; i < lines.length; i++) {
        var d = lines[i].match(/^(\s*)direction\s+(TB|BT|LR|RL)\s*$/);
        if (d) { lines[i] = d[1] + 'direction ' + (/^(LR|RL)$/.test(d[2]) ? 'TB' : 'LR'); return lines.join('\n'); }
      }
      lines.splice(k + 1, 0, '  direction LR');
      return lines.join('\n');
    }
    var m = (lines[k] || '').match(/^(\s*(?:flowchart|graph))(?:\s+(TB|TD|BT|LR|RL))?(.*)$/);
    if (!m) return null;
    lines[k] = m[1] + ' ' + (/^(LR|RL)$/.test(m[2] || 'TB') ? 'TB' : 'LR') + m[3];
    return lines.join('\n');
  }
  function size(svgText){
    var m = svgText.match(/viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)\s*"/);
    return m ? { w: parseFloat(m[1]), h: parseFloat(m[2]) } : null;
  }
  // how large a drawing shows when fitted to the column; very tall drawings count as smaller
  function score(sz, room){
    var s = Math.min(1, room / sz.w), h = sz.h * s, most = window.innerHeight * 1.6;
    return h > most ? s * most / h : s;
  }

  var seq = 0;
  function fitIfClose(fig){
    var out = fig.querySelector('.mmd-out'), svg = out.querySelector('svg');
    if (!svg) return;
    var w = svg.getBoundingClientRect().width, room = out.clientWidth - 24;
    // fit to the column when the diagram is a little too wide; when much wider, keep the natural size and scroll (the text would get too small); full screen is always available
    if (w > room && room / w >= 0.75) setFit(fig, true);
  }
  function setFit(fig, on){
    fig.classList.toggle('fit', on);
    var b = fig.querySelector('.mmd-fit');
    if (b) b.setAttribute('aria-pressed', on ? 'true' : 'false');
  }
  function render(fig){
    if (fig.dataset.state) return;
    fig.dataset.state = 'pending';
    var src = fig.querySelector('.mmd-src').textContent;
    var kind = fig.getAttribute('data-kind');
    var out = fig.querySelector('.mmd-out');
    var id = 'mmd-svg-' + (++seq);
    var ready = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    var mm;
    ready.then(loadMermaid).then(function(mermaid){ mm = mermaid; return mermaid.render(id, src); }).then(function(r){
      var room = out.clientWidth - 24, sz = size(r.svg), alt = flipped(src, kind);
      if (!alt || !sz || sz.w <= room || !/^(flowchart|graph|erDiagram)$/.test(kind)) return r.svg;
      return mm.render(id + 'b', alt).then(function(r2){
        var sz2 = size(r2.svg);
        return sz2 && score(sz2, room) > score(sz, room) * 1.15 ? r2.svg : r.svg;
      }, function(){ return r.svg; });
    }).then(function(svg){
      out.innerHTML = svg;
      fig.dataset.state = 'done';
      if (fig.getAttribute('data-links') === 'flow') linkFlows(fig);
      fitIfClose(fig);
    }).catch(function(e){
      fig.dataset.state = 'error';
      out.textContent = '';
      var p = document.createElement('p');
      p.className = 'mmd-err';
      p.textContent = (UI.draw_failed || '{e}').replace('{e}', String(e && e.message ? e.message : e).split('\n')[0]);
      var pre = document.createElement('pre');
      pre.textContent = src;
      out.appendChild(p);
      out.appendChild(pre);
      ['d' + id, 'd' + id + 'b'].forEach(function(x){ var stray = document.getElementById(x); if (stray) stray.remove(); });
    });
  }
  var figs = document.querySelectorAll('figure.mmd');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function(es){
      es.forEach(function(e){ if (e.isIntersecting) { io.unobserve(e.target); render(e.target); } });
    }, { rootMargin: '400px 0px' });
    figs.forEach(function(f){ io.observe(f); });
  } else {
    figs.forEach(render);
  }
  document.addEventListener('click', function(e){
    var b = e.target.closest('.mmd-fit');
    if (!b) return;
    var fig = b.closest('figure.mmd');
    setFit(fig, !fig.classList.contains('fit'));
  });

  // Threat model: the flow numbers on the arrows (F1, F2…) become links to the threat table's rows, and pointing at
  // one highlights the arrows that carry it
  function linkFlows(fig){
    var svg = fig.querySelector('.mmd-out svg');
    if (!svg) return;
    svg.querySelectorAll('g.edgeLabel g.label[data-id]').forEach(function(g){
      var found = [];
      var walker = document.createTreeWalker(g, NodeFilter.SHOW_TEXT);
      var nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      nodes.forEach(function(t){
        var parts = t.nodeValue.split(/\b(F\d+)\b/);
        if (parts.length < 2) return;
        var frag = document.createDocumentFragment();
        parts.forEach(function(x, i){
          if (i % 2 && document.getElementById('flow-' + x)) {
            var a = document.createElement('a');
            a.className = 'tm-f';
            a.href = '#flow-' + x;
            a.setAttribute('data-flow', x);
            a.textContent = x;
            frag.appendChild(a);
            found.push(x);
          } else if (x) {
            frag.appendChild(document.createTextNode(x));
          }
        });
        t.parentNode.replaceChild(frag, t);
      });
      if (!found.length) return;
      var path = svg.querySelector('[id="' + svg.id + '-' + g.getAttribute('data-id') + '"]');
      if (path) path.setAttribute('data-flows', found.join(' '));
    });
  }
  function markFlow(a, on){
    var f = a.getAttribute('data-flow'), svg = a.closest('svg');
    if (!svg) return;
    svg.querySelectorAll('[data-flows]').forEach(function(p){
      if ((' ' + p.getAttribute('data-flows') + ' ').indexOf(' ' + f + ' ') >= 0) p.classList.toggle('tm-on', on);
    });
    svg.querySelectorAll('a.tm-f[data-flow="' + f + '"]').forEach(function(x){ x.classList.toggle('on', on); });
  }
  ['mouseover', 'focusin'].forEach(function(ev){
    document.addEventListener(ev, function(e){ var a = e.target.closest && e.target.closest('a.tm-f'); if (a) markFlow(a, true); });
  });
  ['mouseout', 'focusout'].forEach(function(ev){
    document.addEventListener(ev, function(e){ var a = e.target.closest && e.target.closest('a.tm-f'); if (a) markFlow(a, false); });
  });

  // full screen: move the diagram into an overlay at natural size, and put it back when closed
  var overlay = null;
  function closeFull(){
    if (!overlay) return;
    var svg = overlay.querySelector('svg');
    if (svg) overlay._home.appendChild(svg);
    overlay._button.focus();
    overlay.remove();
    overlay = null;
    document.body.style.overflow = '';
  }
  document.addEventListener('click', function(e){
    if (overlay && e.target.closest('a.tm-f')) { closeFull(); return; }
    var b = e.target.closest('.mmd-full');
    if (!b) return;
    var fig = b.closest('figure.mmd');
    var out = fig.querySelector('.mmd-out'), svg = out.querySelector('svg');
    if (!svg) return;
    overlay = document.createElement('div');
    overlay.className = 'mmd-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', UI.full_label || '');
    var bar = document.createElement('div');
    bar.className = 'mmd-ov-bar';
    var title = fig.closest('details');
    var t = document.createElement('span');
    t.className = 'mmd-ov-title';
    t.textContent = title ? title.querySelector('summary').textContent : '';
    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'btn';
    close.textContent = UI.close || 'Esc';
    close.addEventListener('click', closeFull);
    bar.appendChild(t);
    bar.appendChild(close);
    var body = document.createElement('div');
    body.className = 'mmd-ov-body';
    body.appendChild(svg);
    overlay.appendChild(bar);
    overlay.appendChild(body);
    overlay._home = out;
    overlay._button = b;
    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';
    close.focus();
  });
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') closeFull(); });

  // latency budgets: a value that does not fit in its segment is hidden; the tooltip and the value table carry it
  function fitLabels(root){
    (root || document).querySelectorAll('.seg').forEach(function(s){
      var i = s.querySelector('i');
      if (!i || !s.offsetParent) return;
      s.classList.remove('nolab');
      if (i.scrollWidth + 6 > s.clientWidth) s.classList.add('nolab');
    });
  }
  document.addEventListener('toggle', function(e){ if (e.target.open) fitLabels(e.target); }, true);
  window.addEventListener('resize', function(){ fitLabels(); });
  fitLabels();
})();
