(function(){
  // Binds to an EXISTING table + controls rendered by the template.
  function toArray(nl){ return Array.prototype.slice.call(nl || []); }
  function parseDate(v){ var d=new Date(v); return isNaN(d.getTime())?null:d.getTime(); }

  function getCell(row, keyOrIndex){
    if (typeof keyOrIndex === 'number') return row.cells[keyOrIndex];
    return row.querySelector('[data-key="'+keyOrIndex+'"]');
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

  function applyFilters(state){
    var q = (state.search.value||'').trim().toLowerCase();
    var s = (state.status.value||'').toLowerCase();
    toArray(state.tbody.rows).forEach(function(r){
      if (r.classList.contains('table-warning')){ r.style.display=''; return; }
      var hay = r.textContent.toLowerCase();
      var okQ = q ? hay.indexOf(q)!==-1 : true;
      var okS = true;
      if (s){
        var txt = (getCell(r, state.statusIdx)?.textContent||'').trim().toLowerCase();
        okS = (txt === s);
      }
      r.style.display = (okQ && okS) ? '' : 'none';
    });
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

  function findStatusIdx(thead){
    var ths = thead.cells;
    for (var i=0;i<ths.length;i++){
      var key = (ths[i].getAttribute('data-key')||'').toLowerCase();
      var txt = (ths[i].textContent||'').trim().toLowerCase();
      if (key==='status' || txt==='status') return i;
    }
    return 3; // default to 4th col
  }

  function bind(opts){
    var table = document.getElementById(opts.tableId);
    if (!table || !table.tBodies || !table.tBodies[0]) return;
    var tbody = table.tBodies[0];
    var thead = table.tHead && table.tHead.rows[0];
    if (!thead) return;

    var status = document.getElementById(opts.statusFilterId);
    var search = document.getElementById(opts.quickSearchId);
    var clear = document.getElementById(opts.clearBtnId);

    var state = {
      thead: thead,
      tbody: tbody,
      status: status,
      search: search,
      sortIdx: -1,
      sortDir: 'asc',
      statusIdx: findStatusIdx(thead)
    };

    attachHeaderSort(state);

    if (opts.defaultSort && typeof opts.defaultSort.index==='number'){
      state.sortIdx = opts.defaultSort.index;
      state.sortDir = (opts.defaultSort.dir==='asc'?'asc':'desc');
      sortRows(state.tbody, state.sortIdx, state.sortDir);
    }

    status.addEventListener('change', function(){ applyFilters(state); });
    search.addEventListener('input', function(){ applyFilters(state); });
    clear.addEventListener('click', function(){ status.value=''; search.value=''; applyFilters(state); });

    applyFilters(state);
  }

  window.bindHistoryEnhancements = bind;
})();