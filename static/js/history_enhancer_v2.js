(function(){
  // HistoryEnhancer v2 — robust & configurable. Non-breaking.
  // Usage (explicit):
  //   <script>
  //     window.HistoryEnhancer && window.HistoryEnhancer.init({
  //       tableSelector: '#historyTable',      // or '.history-table' or 'table'
  //       statusHeaderText: 'Status',          // header text to identify status column
  //       defaultSortIndex: 0,                 // column index to sort by initially
  //       defaultSortDir: 'desc',              // 'asc' | 'desc'
  //       insertControlsBefore: true           // put controls above the table
  //     });
  //   </script>
  //
  // Auto mode (no config) still works: it tries to find a reasonable table and a 'Status' column.

  function toArray(nl){ return Array.prototype.slice.call(nl || []); }
  function uniq(arr){ return Array.from(new Set(arr)); }
  function qs(sel, root){ try { return (root||document).querySelector(sel); } catch(e){ return null; } }

  function findTableAuto(){
    var cands = ['#historyTable','.history-table','main table','.container table','.content table','table'];
    for (var i=0;i<cands.length;i++){
      var t = qs(cands[i]);
      if (t && t.tHead && t.tBodies && t.tBodies[0]) return t;
    }
    return null;
  }

  function findStatusIdx(thead, statusHeaderText){
    var ths = thead ? thead.rows[0].cells : [];
    var want = (statusHeaderText||'Status').trim().toLowerCase();
    for (var i=0;i<ths.length;i++){
      var th = ths[i];
      var key = (th.getAttribute('data-key')||'').toLowerCase();
      var txt = (th.textContent||'').trim().toLowerCase();
      if (key === 'status' || txt === want) return i;
    }
    // fallback: not found
    return -1;
  }

  function buildControls(){
    var wrap = document.createElement('div');
    wrap.className = 'row g-3 align-items-end mb-3 he-controls';
    wrap.innerHTML = ''+
      '<div class="col-md-4">'+
      ' <label class="form-label">Filter by status</label>'+
      ' <select class="form-select he-status"><option value="">All statuses</option></select>'+
      '</div>'+
      '<div class="col-md-4">'+
      ' <label class="form-label">Quick search (any column)</label>'+
      ' <input type="search" class="form-control he-search" placeholder="Type to filter rows…">'+
      '</div>'+
      '<div class="col-md-4 text-md-end">'+
      ' <button type="button" class="btn btn-outline-secondary he-clear">Clear filters</button>'+
      '</div>';
    return wrap;
  }

  function populateStatuses(tbody, idx, selectEl){
    if (!tbody || idx < 0) return;
    var vals = toArray(tbody.rows).map(function(r){
      var c = r.cells[idx];
      return c ? (c.textContent||'').trim() : '';
    }).filter(function(v){ return v.length; });
    uniq(vals).sort().forEach(function(v){
      var opt = document.createElement('option');
      opt.value = v; opt.textContent = v; selectEl.appendChild(opt);
    });
  }

  function parseDate(v){
    var d = new Date(v);
    return isNaN(d.getTime()) ? null : d.getTime();
  }

  function applyFilters(state){
    var q = (state.search.value||'').trim().toLowerCase();
    var s = (state.status.value||'').toLowerCase();
    toArray(state.tbody.rows).forEach(function(r){
      var okQ = true, okS = true;
      if (q){
        var hay = r.textContent.toLowerCase();
        okQ = hay.indexOf(q) !== -1;
      }
      if (s && state.statusIdx >= 0){
        var txt = (r.cells[state.statusIdx]?.textContent||'').trim().toLowerCase();
        okS = (txt === s);
      }
      r.style.display = (okQ && okS) ? '' : 'none';
    });
  }

  function sortBy(state, idx, dir){
    var rows = toArray(state.tbody.rows);
    rows.sort(function(a,b){
      var A = a.cells[idx]?.getAttribute('data-sort') || a.cells[idx]?.textContent || '';
      var B = b.cells[idx]?.getAttribute('data-sort') || b.cells[idx]?.textContent || '';
      var aNum = parseFloat(A), bNum = parseFloat(B);
      var aDate = parseDate(A), bDate = parseDate(B);
      var va, vb;
      if (!isNaN(aNum) && !isNaN(bNum)){ va=aNum; vb=bNum; }
      else if (aDate!==null && bDate!==null){ va=aDate; vb=bDate; }
      else { va=(A+'').toLowerCase(); vb=(B+'').toLowerCase(); }
      if (va<vb) return dir==='asc' ? -1 : 1;
      if (va>vb) return dir==='asc' ? 1 : -1;
      return 0;
    });
    rows.forEach(function(r){ state.tbody.appendChild(r); });
  }

  function attachHeaderSort(state){
    toArray(state.thead.cells).forEach(function(th, idx){
      th.style.cursor = 'pointer';
      th.title = 'Click to sort';
      th.addEventListener('click', function(){
        var dir = (state.sortIdx===idx && state.sortDir==='asc') ? 'desc' : 'asc';
        state.sortIdx = idx; state.sortDir = dir;
        sortBy(state, idx, dir);
        applyFilters(state);
      });
    });
  }

  function banner(el, msg){
    var d = document.createElement('div');
    d.className = 'alert alert-warning py-2 he-banner';
    d.textContent = msg;
    el.parentNode.insertBefore(d, el);
  }

  function init(opts){
    opts = opts || {};
    var table = opts.tableSelector ? qs(opts.tableSelector) : findTableAuto();
    if (!table || !table.tHead || !table.tBodies || !table.tBodies[0]){
      // Non-breaking: show small hint and bail
      var host = qs('main, .container, .content, body');
      if (host) banner(host.firstChild || host, 'HistoryEnhancer: table not found — set tableSelector to your history table.');
      return;
    }

    var thead = table.tHead.rows[0];
    var tbody = table.tBodies[0];

    // Insert controls
    var controls = buildControls();
    if (opts.insertControlsBefore !== false){
      table.parentNode.insertBefore(controls, table);
    } else {
      table.parentNode.insertBefore(controls, table.nextSibling);
    }

    var statusIdx = findStatusIdx(table.tHead, opts.statusHeaderText);
    var select = controls.querySelector('.he-status');
    var search = controls.querySelector('.he-search');
    var clear  = controls.querySelector('.he-clear');
    populateStatuses(tbody, statusIdx, select);

    var state = {
      table: table,
      thead: thead,
      tbody: tbody,
      status: select,
      search: search,
      statusIdx: statusIdx,
      sortIdx: -1,
      sortDir: 'asc'
    };

    select.addEventListener('change', function(){ applyFilters(state); });
    search.addEventListener('input', function(){ applyFilters(state); });
    clear.addEventListener('click', function(){ select.value=''; search.value=''; applyFilters(state); });

    attachHeaderSort(state);

    // Default sort if provided
    if (typeof opts.defaultSortIndex === 'number'){
      var dir = (opts.defaultSortDir === 'asc' ? 'asc' : 'desc');
      state.sortIdx = opts.defaultSortIndex;
      state.sortDir = dir;
      sortBy(state, state.sortIdx, state.sortDir);
    }

    applyFilters(state);
  }

  // Auto-init once, but keep explicit API available.
  function autoInit(){
    if (document.currentScript && document.currentScript.hasAttribute('data-auto') && document.currentScript.getAttribute('data-auto')==='0'){
      return; // explicit only mode
    }
    init({}); // try auto
  }

  if (!window.HistoryEnhancer) window.HistoryEnhancer = { init: init };

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', autoInit);
  } else {
    autoInit();
  }
})();