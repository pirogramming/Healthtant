// 뒤로가기 함수 - diets_search.html로 이동
function goBackToSearch() {
  const urlParams = new URLSearchParams(window.location.search);
  const year = urlParams.get('year') || new Date().getFullYear();
  const month = urlParams.get('month') || new Date().getMonth() + 1;
  
  window.location.href = `/diets/?year=${year}&month=${month}`;
}

function getCookie(name) {
  const v = `; ${document.cookie}`;
  const p = v.split(`; ${name}=`);
  if (p.length === 2) return p.pop().split(";").shift();
}


// 단일 선택 강제
document.addEventListener('DOMContentLoaded', () => {
  const checks = Array.from(document.querySelectorAll('.meal-check'));
  const mealHidden = document.getElementById('mealKrHidden');

  function updateHidden() {
    const picked = checks.find(c => c.checked);
    mealHidden.value = picked ? picked.dataset.value : '';
  }

  checks.forEach(c => {
    c.addEventListener('change', (e) => {
      if (e.target.checked) {
        checks.forEach(o => { if (o !== e.target) o.checked = false; });
      }
      updateHidden();
    });
  });

  // 초기값 세팅
  updateHidden();

  // 기본값: 오늘 날짜
  const dateEl = document.getElementById('date');
  if (dateEl && !dateEl.value) {
    const d = new Date();
    const m = String(d.getMonth()+1).padStart(2,'0');
    const day = String(d.getDate()).padStart(2,'0');
    dateEl.value = `${d.getFullYear()}-${m}-${day}`;
  }
});
