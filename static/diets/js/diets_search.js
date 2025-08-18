// 페이지네이션 변수들
let currentPage = 1;
let hasMoreData = true;
let isLoading = false;
const ITEMS_PER_PAGE = 30;

// 검색 실행
function performSearch() {
    const searchInput = document.getElementById('searchInput');
    const keyword = searchInput.value.trim();
    
    if (!keyword) {
        alert('검색어를 입력해주세요.');
        return;
    }
    
    // 검색 결과 섹션 표시
    const searchResults = document.getElementById('searchResults');
    searchResults.style.display = 'block';
    
    // 검색 결과 로드
    loadSearchResults(keyword, 1);
}

// 검색 결과 로드
async function loadSearchResults(keyword, page) {
    if (isLoading) return;
    
    isLoading = true;
    showLoading();
    hideLoadMoreButton();
    
    try {
        const params = new URLSearchParams({
            keyword: keyword,
            page: page,
            limit: ITEMS_PER_PAGE
        });
        
        const response = await fetch(`/search/normal/?${params}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error('검색 요청 실패');
        }
        
        const data = await response.json();
        
        if (page === 1) {
            // 첫 페이지면 기존 결과 초기화
            displaySearchResults(data.foods);
        } else {
            // 추가 페이지면 기존 결과에 추가
            appendSearchResults(data.foods);
        }
        
        // 더 이상 데이터가 없으면
        if (data.foods.length < ITEMS_PER_PAGE) {
            hasMoreData = false;
        } else {
            showLoadMoreButton();
        }
        
        currentPage = page;
        
    } catch (error) {
        console.error('검색 오류:', error);
        alert('검색 중 오류가 발생했습니다.');
    } finally {
        isLoading = false;
        hideLoading();
    }
}

// 더 많은 결과 로드
function loadMoreResults() {
    const searchInput = document.getElementById('searchInput');
    const keyword = searchInput.value.trim();
    
    if (keyword && hasMoreData && !isLoading) {
        loadSearchResults(keyword, currentPage + 1);
    }
}

// 검색 결과 표시
function displaySearchResults(foods) {
    const resultList = document.getElementById('searchResultsList');
    resultList.innerHTML = '';
    
    if (foods.length === 0) {
        resultList.innerHTML = '<div class="no-results">검색 결과가 없습니다.</div>';
        return;
    }
    
    foods.forEach(food => {
        const foodElement = createFoodElement(food);
        resultList.appendChild(foodElement);
    });
}

// 검색 결과 추가
function appendSearchResults(foods) {
    const resultList = document.getElementById('searchResultsList');
    
    foods.forEach(food => {
        const foodElement = createFoodElement(food);
        resultList.appendChild(foodElement);
    });
}

// 음식 요소 생성
function createFoodElement(food) {
    const foodDiv = document.createElement('div');
    foodDiv.className = 'food-card';
    foodDiv.dataset.foodId = food.food_id;
    
    foodDiv.innerHTML = `
        <div class="food-image">
            ${food.food_img ? `<img src="${food.food_img}" alt="${food.food_name}">` : '<img src="/static/diets/images/default-food.jpg" alt="이미지 없음">'}
        </div>
        <div class="food-info">
            <h3 class="food-name">${food.food_name}</h3>
            <p class="food-company">제조사: ${food.company_name || '제조사 정보 없음'}</p>
        </div>
        <button class="register-btn btn btn-primary" onclick="registerFood('${food.food_id}')">
            <span class="plus-icon">+</span>
            <span class="register-text">등록하기</span>
        </button>
    `;
    
    return foodDiv;
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

// 검색 초기화
function clearSearch() {
    // diets_register.html로 이동
    window.location.href = '/diets/list/';
}

// 로딩 표시
function showLoading() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'block';
    }
}

// 로딩 숨기기
function hideLoading() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
    }
}

// 더보기 버튼 표시
function showLoadMoreButton() {
    const loadMoreContainer = document.getElementById('loadMoreContainer');
    if (loadMoreContainer) {
        loadMoreContainer.style.display = 'block';
    }
}

// 더보기 버튼 숨기기
function hideLoadMoreButton() {
    const loadMoreContainer = document.getElementById('loadMoreContainer');
    if (loadMoreContainer) {
        loadMoreContainer.style.display = 'none';
    }
}

// 엔터키로 검색 실행
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
});