// ========================================
// DIETS JAVASCRIPT
// ========================================

// ========================================
// DIETS SEARCH (diets_search.html)
// ========================================

// 검색 수행 함수
function performSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;
    
    const keyword = searchInput.value.trim();
    
    if (!keyword) {
        alert('검색어를 입력해주세요.');
        return;
    }
    
    // AJAX 요청
    fetch(`/diets/search/?keyword=${encodeURIComponent(keyword)}`)
        .then(response => response.json())
        .then(data => {
            displaySearchResults(data.foods);
        })
        .catch(error => {
            console.error('검색 중 오류가 발생했습니다:', error);
            alert('검색 중 오류가 발생했습니다.');
        });
}

// 검색 결과 표시 함수
function displaySearchResults(foods) {
    const searchResults = document.getElementById('searchResults');
    const searchResultsList = document.getElementById('searchResultsList');
    
    if (!searchResults || !searchResultsList) return;
    
    if (foods.length === 0) {
        searchResultsList.innerHTML = '<div class="no-results">검색 결과가 없습니다.</div>';
    } else {
        searchResultsList.innerHTML = '';
        
        foods.forEach(food => {
            const foodCard = document.createElement('div');
            foodCard.className = 'food-card card';
            foodCard.setAttribute('data-food-id', food.food_id);
            
            foodCard.innerHTML = `
                <div class="food-image">
                    ${food.food_img ? 
                        `<img src="${food.food_img}" alt="${food.food_name}">` : 
                        `<img src="/static/diets/images/default-food.jpg" alt="${food.food_name}">`
                    }
                </div>
                <div class="food-info">
                    <h3 class="food-name">${food.food_name}</h3>
                    <p class="food-company">제조사: ${food.company_name}</p>
                </div>
                <button class="register-btn" onclick="registerFood('${food.food_id}')">
                    <span class="plus-icon">+</span>
                    <span class="register-text">등록하기</span>
                </button>
            `;
            
            searchResultsList.appendChild(foodCard);
        });
    }
    
    searchResults.style.display = 'block';
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

// 검색 취소 함수
function clearSearch() {
    // diets_main.html로 이동 (오늘 날짜로)
    const today = new Date();
    const year = today.getFullYear();
    const month = today.getMonth() + 1;
    
    window.location.href = `/diets/?year=${year}&month=${month}`;
}

// ========================================
// DIETS FORM (diets_form.html)
// ========================================

// 뒤로가기 함수 - diets_search.html로 이동
function goBackToSearch() {
    window.location.href = '/diets/search/page/';
}

// ========================================
// DIETS REGISTER (diets_register.html)
// ========================================

// ========================================
// DIETS MAIN (diets_main.html)
// ========================================

// 쿠키 가져오기 함수
function getCookie(name) {
    const v = `; ${document.cookie}`;
    const p = v.split(`; ${name}=`);
    if (p.length === 2) return p.pop().split(";").shift();
}

// 오늘 날짜 YMD 형식 반환
function todayYMD() {
    const d = new Date();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${m}-${day}`;
}

// 식사 삭제 함수
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

// 식사 수정 함수
async function editMeal(el) {
    const dietId = el.dataset.dietId;
    const curFood = el.dataset.foodId; // 문자열 (uuid 또는 int)
    const curDate = el.dataset.date; // 'YYYY-MM-DD'
    const curMeal = el.dataset.meal; // 'breakfast' | 'lunch' | 'dinner'
    const url = `/diets/form/${dietId}/?date=${encodeURIComponent(curDate)}&meal=${encodeURIComponent(curMeal)}`;
    window.location.href = url;
}

// 월 변경 함수
function changeMonth(direction) {
    // Django에서 전달받은 현재 년도와 월 사용
    let year = window.currentYear || new Date().getFullYear();
    let month = window.currentMonth || new Date().getMonth() + 1;
    
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

// ========================================
// DIETS UPLOAD (diets_upload.html)
// ========================================

// 음식 선택 함수
function selectFood() {
    // 음식 검색 페이지로 이동
    window.location.href = '/diets/search/page/';
}

// ========================================
// 공통 함수들
// ========================================

// 로그인 상태 확인 함수
function checkLoginStatus() {
    return window.isAuthenticated || false;
}

// ========================================
// 페이지 로드 시 초기화
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    // ========================================
    // DIETS SEARCH 초기화
    // ========================================
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault(); // 기본 동작 방지
                performSearch();
            }
        });
    }

    // ========================================
    // DIETS FORM 초기화
    // ========================================
    const mealChecks = Array.from(document.querySelectorAll('.meal-check'));
    const mealHidden = document.getElementById('mealKrHidden');
    
    if (mealChecks.length > 0 && mealHidden) {
        // 단일 선택 강제
        function updateHidden() {
            const picked = mealChecks.find(c => c.checked);
            mealHidden.value = picked ? picked.dataset.value : '';
        }
        
        mealChecks.forEach(c => {
            c.addEventListener('change', (e) => {
                if (e.target.checked) {
                    mealChecks.forEach(o => { if (o !== e.target) o.checked = false; });
                }
                updateHidden();
            });
        });
        
        // 초기값 세팅
        updateHidden();
    }

    // 기본값: 오늘 날짜
    const dateEl = document.getElementById('date');
    if (dateEl && !dateEl.value) {
        const d = new Date();
        const m = String(d.getMonth()+1).padStart(2,'0');
        const day = String(d.getDate()).padStart(2,'0');
        dateEl.value = `${d.getFullYear()}-${m}-${day}`;
    }

    // ========================================
    // DIETS MAIN 초기화
    // ========================================
    // 맨 위로 가기 버튼 기능
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

        // 버튼 클릭 시 맨 위로 스크롤
        scrollToTopBtn.addEventListener('click', function(e) {
            e.preventDefault(); // 링크 기본 동작 방지
            window.scrollTo({
                top: 0,
                left: 0,
                behavior: 'instant' // smooth 대신 instant 사용
            });
        });
    }

    // "새 식사" / "오늘의 식사 추가하기" → register 페이지로 이동
    const addMealBtn = document.querySelector(".add-meal-btn");
    if (addMealBtn) {
        addMealBtn.addEventListener("click", () => {
            // 기본: 오늘 날짜만 세팅. 음식/끼니는 register 페이지에서 선택.
            window.location.href = `/diets/list/?date=${todayYMD()}`;
        });
    }

    const addTodayMeal = document.querySelector(".add-today-meal");
    if (addTodayMeal) {
        addTodayMeal.addEventListener("click", () => {
            window.location.href = `/diets/list/?date=${todayYMD()}`;
        });
    }

    // ========================================
    // DIETS UPLOAD 초기화
    // ========================================
    const dietForm = document.getElementById('dietForm');
    if (dietForm) {
        // 폼 제출 시 날짜와 끼니 검증
        dietForm.addEventListener('submit', function(e) {
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
    }


});
