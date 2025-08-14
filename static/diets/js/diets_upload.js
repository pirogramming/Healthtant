
  function selectFood() {
    // 음식 검색 페이지로 이동
    window.location.href = '/diets/search/page/';
  }

  // 단일 선택 강제
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
  (function initDate() {
    const dateEl = document.getElementById('date');
    if (!dateEl.value) {
      const d = new Date();
      const m = String(d.getMonth()+1).padStart(2,'0');
      const day = String(d.getDate()).padStart(2,'0');
      dateEl.value = `${d.getFullYear()}-${m}-${day}`;
    }
  })();

  // 폼 제출 시 날짜와 끼니 검증
  document.getElementById('dietForm').addEventListener('submit', function(e) {
      const dateValue = document.getElementById('date').value;
      const mealValue = document.getElementById('mealKrHidden').value;
      
      if (!dateValue) {
          e.preventDefault();
          alert('날짜를 선택해주세요.');
          return false;
      }
      
      if (!mealValue) {
          e.preventDefault();
          alert('끼니를 선택해주세요.');
          return false;
      }
  });