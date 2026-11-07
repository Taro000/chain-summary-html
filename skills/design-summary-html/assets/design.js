// design-summary-html: additions to base.js (a copy of quality-summary-html's summary.js)
(function(){
  var MERMAID_URL = '__MERMAID_URL__';

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

  // 「すべて開く」 and 「すべて閉じる」 also open and close the nested toggles
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
        mermaid.initialize({
          startOnLoad: false, securityLevel: 'strict', suppressErrorRendering: true, theme: 'base',
          fontFamily: v('--f-body'),
          themeVariables: {
            fontFamily: v('--f-body'), fontSize: '13px',
            primaryColor: v('--route-soft'), primaryBorderColor: v('--route'), primaryTextColor: v('--ink'),
            secondaryColor: v('--head'), secondaryBorderColor: v('--rule'), tertiaryColor: v('--surface'),
            tertiaryBorderColor: v('--rule'), lineColor: v('--ink-3'), textColor: v('--ink'),
            mainBkg: v('--route-soft'), nodeBorder: v('--route'), clusterBkg: v('--paper'), clusterBorder: v('--rule'),
            titleColor: v('--ink'), edgeLabelBackground: v('--surface'),
            actorBkg: v('--route-soft'), actorBorder: v('--route'), actorTextColor: v('--ink'), actorLineColor: v('--rule'),
            signalColor: v('--ink-2'), signalTextColor: v('--ink'), labelBoxBkgColor: v('--head'),
            labelBoxBorderColor: v('--rule'), labelTextColor: v('--ink'), loopTextColor: v('--ink-2'),
            noteBkgColor: v('--note-bg'), noteBorderColor: v('--note-line'), noteTextColor: v('--ink'),
            activationBkgColor: v('--route-soft'), activationBorderColor: v('--route'), sequenceNumberColor: '#ffffff',
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
    var out = fig.querySelector('.mmd-out');
    var id = 'mmd-svg-' + (++seq);
    var ready = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    ready.then(loadMermaid).then(function(mermaid){ return mermaid.render(id, src); }).then(function(r){
      out.innerHTML = r.svg;
      fig.dataset.state = 'done';
      fitIfClose(fig);
    }).catch(function(e){
      fig.dataset.state = 'error';
      out.textContent = '';
      var p = document.createElement('p');
      p.className = 'mmd-err';
      p.textContent = '図を描けませんでした（' + String(e && e.message ? e.message : e).split('\n')[0] + '）。もとの記述を示します。';
      var pre = document.createElement('pre');
      pre.textContent = src;
      out.appendChild(p);
      out.appendChild(pre);
      var stray = document.getElementById('d' + id);
      if (stray) stray.remove();
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
    var b = e.target.closest('.mmd-full');
    if (!b) return;
    var fig = b.closest('figure.mmd');
    var out = fig.querySelector('.mmd-out'), svg = out.querySelector('svg');
    if (!svg) return;
    overlay = document.createElement('div');
    overlay.className = 'mmd-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', '図を全画面で見る');
    var bar = document.createElement('div');
    bar.className = 'mmd-ov-bar';
    var title = fig.closest('details');
    var t = document.createElement('span');
    t.className = 'mmd-ov-title';
    t.textContent = title ? title.querySelector('summary').textContent : '';
    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'btn';
    close.textContent = '閉じる（Esc）';
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

  // threat model figure: hovering or focusing a flow chip highlights its line
  function mark(chip, on){
    var f = chip.getAttribute('data-flow');
    chip.classList.toggle('on', on);
    document.querySelectorAll('.tm-flow').forEach(function(p){
      if ((' ' + p.getAttribute('data-flows') + ' ').indexOf(' ' + f + ' ') >= 0) p.classList.toggle('on', on);
    });
  }
  document.addEventListener('mouseover', function(e){ var c = e.target.closest && e.target.closest('.tm-chip'); if (c) mark(c, true); });
  document.addEventListener('mouseout', function(e){ var c = e.target.closest && e.target.closest('.tm-chip'); if (c) mark(c, false); });
  document.addEventListener('focusin', function(e){ var c = e.target.closest && e.target.closest('.tm-chip'); if (c) mark(c, true); });
  document.addEventListener('focusout', function(e){ var c = e.target.closest && e.target.closest('.tm-chip'); if (c) mark(c, false); });
})();
