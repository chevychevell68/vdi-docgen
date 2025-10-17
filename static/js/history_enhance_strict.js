(function(){
  var LOADED = false;
  function toArray(nl){ return Array.prototype.slice.call(nl || []); }
  function uniq(arr){ return Array.from(new Set(arr)); }
  function parseDate(v){ var d=new Date(v); return isNaN(d.getTime())?null:d.getTime(); }

  function buildControls(){
    var wrap = document.createElement('div');
    wrap.id = 'he-controls';
    wrap.className = 'row g-3 align-items-end mb-3';
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

  function statusIndex(thead){
    var ths = thead.cells;
    for (var i=0;i<ths.length;i++){
      var txt = (ths[i].textContent||'').trim().toLowerCase();
      if (txt === 'status') return i;
    }
    return -1;
  }

  function populateStatuses(tbody, idx, selectEl){
    if (idx < 0) return;
    var vals = toArray(tbody.rows).map(function(r){
      return (r.cells[idx]?.textContent||'').trim();
    }).filter(Boolean);
    uniq(vals).sort().forEach(function(v){
      var opt = document.createElement('option');
      opt.value = v; opt.textContent = v; selectEl.appendChild(opt);
    });
  }

  function applyFilters(state){
    var q = (state.search.value||'').trim().toLowerCase();
    var s = (state.status.value||'').toLowerCase();
    toArray(state.tbody.rows).forEach(function(r){
      if (r.classList.contains('table-warning')) { r.style.display=''; return; }
      var hay = r.textContent.toLowerCase();
      var okQ = q ? hay.indexOf(q)!==-1 : true;
      var okS = true;
      if (s && state.statusIdx>=0){
        var txt = (r.cells[state.statusIdx]?.textContent||'').trim().toLowerCase();
        okS = (txt === s);
      }
      r.style.display = (okQ && okS) ? '' : 'none';
    });
  }

  function sortRows(tbody, idx, dir){
    var rows = toArray(tbody.rows).filter(function(r){ return !r.classList.contains('table-warning'); });
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
    rows.forEach(function(r){ tbody.appendChild(r); });
  }

  function attachHeaderSort(state){
    toArray(state.thead.cells).forEach(function(th, idx){
      th.style.cursor = 'pointer';
      th.title = 'Click to sort';
      th.addEventListener('click', function(){
        state.sortIdx = idx;
        state.sortDir = (state.sortIdx===idx && state.sortDir==='asc') ? 'desc' : 'asc';
        sortRows(state.tbody, idx, state.sortDir);
        applyFilters(state);
      });
    });
  }

  function init(opts){
    if (LOADED) return; LOADED = true;
    var table = document.querySelector(opts.tableSelector || '#historyTable');
    if (!table || !table.tBodies || !table.tBodies[0]) return;
    var tbody = table.tBodies[0];
    var thead = table.tHead && table.tHead.rows[0];
    if (!thead) return;
    if (tbody.rows.length === 0 || (tbody.rows.length === 1 && tbody.rows[0].classList.contains('table-warning'))) return;
    if (document.getElementById('he-controls')) return;

    var controls = buildControls();
    table.parentNode.insertBefore(controls, table);

    var state = {
      thead: thead,
      tbody: tbody,
      status: controls.querySelector('.he-status'),
      search: controls.querySelector('.he-search'),
      sortIdx: -1,
      sortDir: 'asc',
      statusIdx: statusIndex(thead)
    };

    populateStatuses(tbody, state.statusIdx, state.status);
    attachHeaderSort(state);

    if (typeof opts.defaultSortIndex === 'number'){
      var dir = (opts.defaultSortDir === 'asc' ? 'asc' : 'desc');
      sortRows(state.tbody, opts.defaultSortIndex, dir);
      state.sortIdx = opts.defaultSortIndex;
      state.sortDir = dir;
    }

    state.status.addEventListener('change', function(){ applyFilters(state); });
    state.search.addEventListener('input', function(){ applyFilters(state); });
    controls.querySelector('.he-clear').addEventListener('click', function(){
      state.status.value=''; state.search.value=''; applyFilters(state);
    });
  }

  window.HistoryEnhanceStrict = { init: init };
})();