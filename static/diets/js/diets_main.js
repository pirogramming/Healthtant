function getCookie(name) {
    const v = `; ${document.cookie}`;
    const p = v.split(`; ${name}=`);
    if (p.length === 2) return p.pop().split(";").shift();
}
function goBackToSearch() {
    window.location.href = '/diets/search/page/';
  }
// 검색 페이지로 이동
function performSearch() {
    window.location.href = '/diets/search/page/';
  }

// 식사 검색 페이지로 이동
function goToDietsSearch() {
    window.location.href = '/diets/search/page/';
  }

function clearSearch() {
    const today = new Date();
    const year = today.getFullYear();
    const month = today.getMonth() + 1;

    window.location.href = `/diets/?year=${year}&month=${month}`;
}
// 음식 등록 함수
function registerFood(foodId) {
    // 오늘 날짜 생성
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    const todayString = `${year}-${month}-${day}`;
    
    // diets_upload.html로 이동 (food_id와 오늘 날짜를 파라미터로 전달)
    window.location.href = `/diets/upload/?food=${foodId}&date=${todayString}`;
}
  

// 맨 위로 가기 버튼 기능
document.addEventListener('DOMContentLoaded', () => {
  const scrollToTopBtn = document.getElementById('scrollToTopBtn');
  
  if (scrollToTopBtn) {
    // 스크롤 이벤트 리스너
    window.addEventListener('scroll', () => {
      if (window.pageYOffset > 1) {
        scrollToTopBtn.classList.add('show');
      } else {
        scrollToTopBtn.classList.remove('show');
      }
    });

    // 버튼 클릭 시 맨 위로 스크롤 (a태그용)
    scrollToTopBtn.addEventListener('click', function(e) {
      e.preventDefault(); // 링크 기본 동작 방지
      window.scrollTo({
        top: 0,
        left: 0,
        behavior: 'instant' // smooth 대신 instant 사용
      });
    });
  }
});

async function deleteMeal(el) {
  const id = el.dataset.dietId;
  console.log(id);
  const res = await fetch(`/diets/${id}/`, {
    method: "DELETE",
    headers: { "X-CSRFToken": getCookie("csrftoken") },
  });
  if (res.status === 204) {
    el.closest(".meal-item")?.remove(); // 또는: location.reload();
  } else {
    alert(`삭제 실패 (${res.status})`);
  }
}

async function editMeal(el) {
  const dietId = el.dataset.dietId;
  const curFood = el.dataset.foodId; // 문자열 (uuid 또는 int)
  const curDate = el.dataset.date; // 'YYYY-MM-DD'
  const curMeal = el.dataset.meal; // 'breakfast' | 'lunch' | 'dinner'
  const url = `/diets/form/${dietId}/?date=${encodeURIComponent(curDate)}&meal=${encodeURIComponent(curMeal)}`;
  window.location.href = url;
}

// 프롬프트로 새 값 입력(엔터 치면 기존값 유지)
function todayYMD() {
    const d = new Date();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${m}-${day}`;
}

// 로그인 상태 확인 함수
function checkLoginStatus() {
    // Django 템플릿 변수를 전역 변수로 설정해야 함
    return window.isUserAuthenticated;
}

// 로그인이 필요한 기능에 적용할 함수
function requireLogin(callback) {
    if (checkLoginStatus()) {
        // 로그인된 경우 원래 기능 실행
        if (callback) callback();
    } else {
        // 로그인되지 않은 경우 모달 표시
        showLoginModal();
    }
}

// 페이지 접근 시 로그인 체크
document.addEventListener('DOMContentLoaded', function() {
    if (!checkLoginStatus()) {
        showLoginModal();
    }
});

// "새 식사" / "오늘의 식사 추가하기" → register 페이지로 이동 (로그인된 경우에만)
document.addEventListener('DOMContentLoaded', () => {
  document.querySelector(".add-meal-btn")?.addEventListener("click", () => {
      if (checkLoginStatus()) {
          // 기본: 오늘 날짜만 세팅. 음식/끼니는 register 페이지에서 선택.
          window.location.href = `/diets/list/?date=${todayYMD()}`;
      }
  });

  document.querySelector(".add-today-meal")?.addEventListener("click", () => {
      if (checkLoginStatus()) {
          window.location.href = `/diets/list/?date=${todayYMD()}`;
      }
  });
});

// 월 변경 함수
function changeMonth(direction) {
    // Django에서 전달받은 현재 년도와 월을 전역 변수로 설정해야 함
    let year = window.currentYear;
    let month = window.currentMonth;
    
    month += direction;
    
    if (month > 12) {
        month = 1;
        year++;
    } else if (month < 1) {
        month = 12;
        year--;
    }
    
    // URL 파라미터로 년도와 월을 전달하여 페이지 새로고침
    const currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set('year', year);
    currentUrl.searchParams.set('month', month);
    window.location.href = currentUrl.toString();
}
