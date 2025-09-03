// Simple static app to visualize and filter hierarchical categories

const state = {
  tree: null,
  // Map from node id to DOM elements and checkbox
  domIndex: new Map(),
};

// Utility to create elements
function h(tag, props = {}, ...children){
  const el = document.createElement(tag);
  for(const [k,v] of Object.entries(props)){
    if(k === 'class') el.className = v;
    else if(k === 'text') el.textContent = v;
    else if(k.startsWith('on') && typeof v === 'function') el.addEventListener(k.substring(2), v);
    else if(k === 'attrs' && v && typeof v === 'object'){
      for(const [ak,av] of Object.entries(v)) el.setAttribute(ak, av);
    } else if(k in el){
      el[k] = v;
    } else {
      el.setAttribute(k, v);
    }
  }
  for(const c of children){
    if(c == null) continue;
    if(Array.isArray(c)) el.append(...c);
    else if(typeof c === 'string') el.append(document.createTextNode(c));
    else el.append(c);
  }
  return el;
}

// Build a generic N-level tree from an array of pipe-separated paths
function buildTree(paths){
  let nextId = 1;
  const root = { id: 0, name: 'ROOT', full: '', children: new Map(), parent: null, depth: -1, checked: false, indeterminate: false };

  for(const raw of paths){
    if(!raw || typeof raw !== 'string') continue;
    const parts = raw.split('|').map(s => s.trim()).filter(Boolean);
    if(parts.length === 0) continue;
    let node = root;
    let full = '';
    for(let i=0; i<parts.length; i++){
      const part = parts[i];
      full = full ? `${full}|${part}` : part;
      if(!node.children.has(part)){
        const child = { id: nextId++, name: part, full, children: new Map(), parent: node, depth: node.depth + 1, checked: false, indeterminate: false };
        node.children.set(part, child);
        node = child;
      } else {
        node = node.children.get(part);
      }
    }
  }
  return root;
}

function renderTree(root){
  const container = document.getElementById('tree');
  container.innerHTML = '';

  const ul = h('ul', { class: 'tree-root' });
  container.append(ul);

  function renderNode(node){
    if(node.id === 0){
      // render children of root only
      for(const child of node.children.values()){
        ul.append(renderNode(child));
      }
      return ul;
    }
    const hasChildren = node.children.size > 0;
    const li = h('li', { class: `node depth-${Math.max(0, node.depth)}` });

    const toggle = h('span', { class: 'toggle' + (hasChildren ? '' : ' empty'), attrs: { role: 'button', tabindex: hasChildren ? 0 : -1, 'aria-label': hasChildren ? 'Espandi/Comprimi' : '' } }, hasChildren ? '▸' : '');
    const checkbox = h('input', { type: 'checkbox' });
    const label = h('span', { class: 'label' }, node.name);

    const row = h('div', { class: 'node-row' }, toggle, checkbox, label);
    li.append(row);
    if(hasChildren){
      const childrenUl = h('ul', { class: 'children' });
      // collapsed by default for deep trees? Keep expanded by default; we control via toggle
      for(const child of node.children.values()){
        childrenUl.append(renderNode(child));
      }
      li.append(childrenUl);
    }

    // Save DOM refs
    state.domIndex.set(node.id, { li, checkbox, toggle, label, node });

    // Events
    if(hasChildren){
      const childrenUl = li.querySelector(':scope > ul.children');
      let expanded = node.depth <= 0; // expand top-level by default
      function updateToggle(){ toggle.textContent = expanded ? '▾' : '▸'; childrenUl.style.display = expanded ? '' : 'none'; }
      toggle.addEventListener('click', () => { expanded = !expanded; updateToggle(); });
      toggle.addEventListener('keydown', (e) => { if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); expanded = !expanded; updateToggle(); }});
      updateToggle();
    }

    checkbox.addEventListener('change', () => {
      setCheckedRecursive(node, checkbox.checked);
      updateAncestors(node.parent);
      refreshSelectionList();
    });

    return li;
  }

  renderNode(root);
}

// Set checked on node and all descendants
function setCheckedRecursive(node, checked){
  node.checked = checked;
  node.indeterminate = false;
  const entry = state.domIndex.get(node.id);
  if(entry){
    entry.checkbox.checked = checked;
    entry.checkbox.indeterminate = false;
  }
  for(const child of node.children.values()){
    setCheckedRecursive(child, checked);
  }
}

// Update ancestors' tri-state based on children
function updateAncestors(node){
  if(!node || node.id === 0) return;
  const children = Array.from(node.children.values());
  const allChecked = children.every(c => c.checked);
  const noneChecked = children.every(c => !c.checked && !c.indeterminate);
  node.checked = allChecked;
  node.indeterminate = !allChecked && !noneChecked;

  const entry = state.domIndex.get(node.id);
  if(entry){
    entry.checkbox.checked = node.checked;
    entry.checkbox.indeterminate = node.indeterminate;
  }
  updateAncestors(node.parent);
}

// Filtering: show nodes that match query or have descendant match
function applyFilter(query){
  const q = query.trim().toLowerCase();
  if(!state.tree) return;
  for(const { li } of state.domIndex.values()) li.classList.remove('hidden');
  if(!q){
    return;
  }
  // DFS: mark visible if self or descendant matches; else hide
  function matches(node){
    const selfMatch = node.name.toLowerCase().includes(q) || node.full.toLowerCase().includes(q);
    if(selfMatch) return true;
    for(const c of node.children.values()) if(matches(c)) return true;
    return false;
  }
  function updateVisibility(node){
    if(node.id === 0){
      for(const c of node.children.values()) updateVisibility(c);
      return;
    }
    const visible = matches(node);
    const entry = state.domIndex.get(node.id);
    if(entry){ entry.li.classList.toggle('hidden', !visible); }
    for(const c of node.children.values()) updateVisibility(c);
  }
  updateVisibility(state.tree);
}

// Collect selected leaf full paths
function collectSelectedLeaves(){
  const out = [];
  function dfs(node){
    if(node.id !== 0){
      if(node.children.size === 0){
        if(node.checked) out.push(node.full);
      } else {
        // If a parent is fully checked, we still want leaves only
        for(const c of node.children.values()) dfs(c);
      }
    } else {
      for(const c of node.children.values()) dfs(c);
    }
  }
  dfs(state.tree);
  return out;
}

function refreshSelectionList(){
  const list = collectSelectedLeaves().sort((a,b) => a.localeCompare(b, 'it'));
  const txt = list.join('\n');
  document.getElementById('selectedList').value = txt;
  document.getElementById('selectedCount').textContent = String(list.length);
}

function expandOrCollapseAll(expand){
  for(const entry of state.domIndex.values()){
    const li = entry.li;
    const childUl = li.querySelector(':scope > ul.children');
    if(childUl){
      childUl.style.display = expand ? '' : 'none';
      entry.toggle.textContent = expand ? '▾' : '▸';
    }
  }
}

function clearAllSelections(){
  if(!state.tree) return;
  for(const child of state.tree.children.values()) setCheckedRecursive(child, false);
  refreshSelectionList();
}

async function init(){
  const container = document.getElementById('tree');
  try{
    const res = await fetch('categorie_uniche.json', { cache: 'no-store' });
    const data = await res.json();
    const paths = Array.isArray(data) ? data : [];
    state.tree = buildTree(paths);
    renderTree(state.tree);
    container.setAttribute('aria-busy', 'false');
  }catch(err){
    container.innerHTML = '';
    container.append(h('div', { class: 'loading' }, 'Errore nel caricamento di categorie_uniche.json. ' + String(err)));
  }

  const search = document.getElementById('search');
  search.addEventListener('input', () => applyFilter(search.value));

  document.getElementById('expandAll').addEventListener('click', () => expandOrCollapseAll(true));
  document.getElementById('collapseAll').addEventListener('click', () => expandOrCollapseAll(false));
  document.getElementById('clearSelection').addEventListener('click', clearAllSelections);

  const copyBtn = document.getElementById('copySelection');
  const output = document.getElementById('selectedList');
  const feedback = document.getElementById('copyFeedback');
  copyBtn.addEventListener('click', async () => {
    try{
      const text = output.value;
      if(!text){ return; }
      if(navigator.clipboard?.writeText){
        await navigator.clipboard.writeText(text);
      } else {
        // fallback
        output.select();
        document.execCommand('copy');
        output.selectionEnd = output.selectionStart; // deselect
      }
      feedback.hidden = false;
      feedback.textContent = 'Copiato!';
      setTimeout(() => { feedback.hidden = true; }, 1200);
    }catch(e){
      feedback.hidden = false;
      feedback.textContent = 'Copia non riuscita';
      setTimeout(() => { feedback.hidden = true; }, 1600);
    }
  });
}

document.addEventListener('DOMContentLoaded', init);
