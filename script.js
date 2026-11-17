(() => {
 const input = document.getElementById('paper-search');
 if(input) {
  const papers = [...document.querySelectorAll('.publication')];
  const status = document.getElementById('search-status');
  const update = () => {
   const query = input.value.trim().toLowerCase();
   let count = 0;
   papers.forEach(p => {p.hidden = !p.textContent.toLowerCase().includes(query); if(!p.hidden) count++;});
   status.textContent = `${count} / ${papers.length} publications`;
  };
  input.addEventListener('input', update); update();
 }
})();
