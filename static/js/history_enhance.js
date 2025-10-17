(function(){
  // HistoryEnhancer: add sort + status filter without changing templates.
  // It auto-detects the history table and a 'Status' column.

  function toArray(nl){ return Array.prototype.slice.call(nl || []); }
  function uniq(arr){ return Array.from(new Set(arr)); }

  function findTable(){
    // Prefer #historyTable, then .history-table, else first table in content
    var t = document.getElementById('historyTable');
    if (t) return t;
    t = document.querySelector('table.history-table');
    if (t) return t;
    return document.querySelector('main table, .container table, .content table, table');
  }

  function findStatusColIndex(table){
    var ths = table.tHead ? table.tHead.rows[0].cells : [];
    for (var i=0;i<ths.length;i++){
      var h = ths[i];
      var key = h.getAttribute('data-key') || '';
      var txt = (h.textContent || '').trim().toLowerCase();
      if (key.toLowerCase() === 'status' || txt === 'status') return i;
    }
    return -1;
  }

  function buildControlRow(){
    var wrap = document.createElement('div');
    wrap.className = 'row g-3 align-items-end mb-3';
    wrap.innerHTML = ''
      + '<div class="col-md-4">'
      + '  <label class="form-label">Filter by status</label>'
      + '  <select class="form-select he-status"><option value="">All statuses</option></select>'
      + '</div>'
      + '<div class="col-md-4">'
      + '  <label class="form-label">Quick search (any column)</label>'
      + '  <input type="search" class="form-control he-search" placeholder="Type to filter rows…">'
      + '</div>'
      + '<div class="col-md-4 text-md-end">'
      + '  <button type="button" class="btn btn-outline-secondary he-clear">Clear filters</button>'
      + '</div>';
    return wrap;
  }

  function populateStatuses(table, statusIdx, selectEl){
    if (!table.tBodies || !table.tBodies[0]) return;
    var vals = toArray(table.tBodies[0].rows).map(function(r){
      var c = r.cells[statusIdx];
      return c ? (c.textContent || '').trim() : '';
    }).filter(function(x){ return x.length; });
    uniq(vals).sort().forEach(function(v){
      var opt = document.createElement('option');
      opt.value = v;
      opt.textContent = v;
      selectEl.appendChild(opt);
    });
  }

  function applyFilters(state){
    var q = (state.search.value || '').trim().toLowerCase();
    var s = (state.status.value || '').toLowerCase();
    toArray(state.tbody.rows).forEach(function(r){
      var hay = r.textContent.toLowerCase();
      var okQ = q ? hay.indexOf(q) !== -1 : true;
      var okS = true;
      if (s && state.statusIdx >= 0){
        var txt = (r.cells[state.statusIdx]?.textContent || '').trim().toLowerCase();
        okS = (txt === s);
      }
      r.style.display = (okQ && okS) ? '' : 'none';
    });
  }

  function parseDate(v){
    var d = new Date(v);
    return isNaN(d.getTime()) ? null : d.getTime();
  }

  function attachSorting(state){
    toArray(state.thead.cells).forEach(function(th, idx){
      th.style.cursor = 'pointer';
      th.title = 'Click to sort';
      th.addEventListener('click', function(){
        var dir = (state.sortIdx===idx && state.sortDir==='asc') ? 'desc' : 'asc';
        state.sortIdx = idx; state.sortDir = dir;
        var rows = toArray(state.tbody.rows);
        rows.sort(function(a,b){
          var A = a.cells[idx]?.getAttribute('data-sort') || a.cells[idx]?.textContent || '';
          var B = b.cells[idx]?.getAttribute('data-sort') || b.cells[idx]?.textContent || '';
          var aNum = parseFloat(A), bNum = parseFloat(B);
          var aDate = parseDate(A), bDate = parseDate(B);
          var va, vb;
          if (!isNaN(aNum) && !isNaN(bNum)){ va=aNum; vb=bNum; }
          else if (aDate!==null && bDate!==null){ va=aDate; vb=bDate; }
          else { va=A.toLowerCase(); vb=B.toLowerCase(); }
          if (va<vb) return dir==='asc' ? -1 : 1;
          if (va>vb) return dir==='asc' ? 1 : -1;
          return 0;
        });
        rows.forEach(function(r){ state.tbody.appendChild(r); });
        applyFilters(state);
      });
    });
  }

  function init(){
    var table = findTable();
    if (!table || !table.tHead || !table.tBodies || !table.tBodies[0]) return;

    var statusIdx = findStatusColIndex(table);
    // Build controls and insert right before table
    var controls = buildControlRow();
    table.parentNode.insertBefore(controls, table);

    var select = controls.querySelector('.he-status');
    var search = controls.querySelector('.he-search');
    var clear  = controls.querySelector('.he-clear');
    populateStatuses(table, statusIdx, select);

    var state = {
      table: table,
      thead: table.tHead.rows[0],
      tbody: table.tBodies[0],
      status: select,
      search: search,
      statusIdx: statusIdx,
      sortIdx: -1,
      sortDir: 'asc'
    };

    select.addEventListener('change', function(){ applyFilters(state); });
    search.addEventListener('input', function(){ applyFilters(state); });
    clear.addEventListener('click', function(){
      select.value = '';
      search.value = '';
      applyFilters(state);
    });

    attachSorting(state);
    applyFilters(state);
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
