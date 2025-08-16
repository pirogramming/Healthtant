// CSRF 토큰 가져오기
const getCookie = (name) => {
    const m = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[2]) : '';
};

const getCsrfToken = () => getCookie('csrftoken');

// 무한 스크롤 관련 변수
let currentPage = 1;
let isLoading = false;
let hasMoreData = true;
let currentSearchKeyword = '';
const ITEMS_PER_PAGE = 30;

function performSearch() {
    const searchInput = document.getElementById('searchInput');
    const keyword = searchInput.value.trim();
    
    if (!keyword) {
        alert('검색어를 입력해주세요.');
        return;
    }
    
    // 새로운 검색이므로 초기화
    currentPage = 1;
    hasMoreData = true;
    currentSearchKeyword = keyword;
    
    // 검색 결과 초기화
    const searchResultsList = document.getElementById('searchResultsList');
    const searchResults = document.getElementById('searchResults');
    
    searchResultsList.innerHTML = '';
    searchResults.style.display = 'block';
    hideLoadMoreButton();
    
    // 첫 번째 페이지 로드
    loadMoreResults();
}

// 더 많은 결과 로드
async function loadMoreResults() {
    if (isLoading || !hasMoreData || !currentSearchKeyword) return;
    
    console.log(`페이지 로드: ${currentPage}, 검색어: ${currentSearchKeyword}`);
    
    isLoading = true;
    showLoadingIndicator();
    hideLoadMoreButton();
    
    try {
        const response = await fetch(`/search/normal/?keyword=${encodeURIComponent(currentSearchKeyword)}&page=${currentPage}&limit=${ITEMS_PER_PAGE}`);
        const data = await response.json();
        
        console.log(`받은 데이터: ${data.foods.length}개 제품`);
        
        if (data.foods.length === 0) {
            hasMoreData = false;
            console.log('더 이상 데이터가 없습니다.');
            if (currentPage === 1) {
                // 첫 페이지에서 결과가 없으면
                displayNoResults();
            }
        } else {
            displaySearchResults(data.foods);
            
            // 더 이상 데이터가 없으면
            if (data.foods.length < ITEMS_PER_PAGE) {
                hasMoreData = false;
                console.log('마지막 페이지입니다.');
            } else {
                showLoadMoreButton();
                console.log('더보기 버튼을 표시합니다.');
            }
            
            currentPage++;
        }
    } catch (error) {
        console.error('검색 중 오류가 발생했습니다:', error);
        alert('검색 중 오류가 발생했습니다.');
    } finally {
        isLoading = false;
        hideLoadingIndicator();
    }
}

// 검색 결과 표시 (기존 결과에 추가)
function displaySearchResults(foods) {
    const searchResults = document.getElementById('searchResults');
    const searchResultsList = document.getElementById('searchResultsList');
    
    // 첫 페이지가 아니면 기존 결과에 추가
    if (currentPage > 1) {
        // 기존 no-results 메시지 제거
        const noResults = searchResultsList.querySelector('.no-results');
        if (noResults) {
            noResults.remove();
        }
    }
    
    foods.forEach(food => {
        const foodCard = document.createElement('div');
        foodCard.className = 'food-card';
        foodCard.setAttribute('data-food-id', food.food_id);
        
        foodCard.innerHTML = `
            <div class="food-image">
                ${food.food_img ? 
                    `<img src="${food.food_img}" alt="${food.food_name}">` : 
                    `<img src="/static/diets/images/default-food.jpg" alt="${food.food_name}">`
                }
            </div>
            <div class="food-info">
                <div class="food-header">
                    <div class="brand-tag">등급 계산 중...</div>
                    <div class="food-text-container">
                        <h3 class="food-name">${food.food_name}</h3>
                        <p class="food-company">제조사: ${food.company_name}</p>
                    </div>
                </div>
            </div>
            <button class="favorite-btn" data-product-id="${food.food_id}" data-is-favorite="${food.is_favorite || 'false'}" type="button" aria-pressed="${food.is_favorite || 'false'}" aria-label="즐겨찾기">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
                    <path class="heart-path" d="M20.84 4.61C20.3292 4.099 19.7228 3.69364 19.0554 3.41708C18.3879 3.14052 17.6725 2.99817 16.95 2.99817C16.2275 2.99817 15.5121 3.14052 14.8446 3.41708C14.1772 3.69364 13.5708 4.099 13.06 4.61L12 5.67L10.94 4.61C9.9083 3.5783 8.50903 2.9987 7.05 2.9987C5.59096 2.9987 4.19169 3.5783 3.16 4.61C2.1283 5.6417 1.5487 7.04097 1.5487 8.5C1.5487 9.95903 2.1283 11.3583 3.16 12.39L12 21.23L20.84 12.39C21.351 11.8792 21.7564 11.2728 22.0329 10.6054C22.3095 9.93789 22.4518 9.22249 22.4518 8.5C22.4518 7.77751 22.3095 7.0621 22.0329 6.39464C21.7564 5.72718 21.351 5.12075 20.84 4.61Z"/>
                </svg>
            </button>
        `;

        // 카드 클릭 → 상세 페이지 이동
        foodCard.addEventListener('click', function(e) {
            // 버튼 클릭 시는 이동 막기
            if (e.target.closest('.favorite-btn')) return;
            window.location.href = `/products/${food.food_id}`;
        });
        
        searchResultsList.appendChild(foodCard);
        
        // 좋아요 버튼 이벤트 리스너 추가
        const favoriteBtn = foodCard.querySelector('.favorite-btn');
        if (favoriteBtn) {
            favoriteBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                toggleFavorite(favoriteBtn);
            });
        }
        
        // 등급 정보 로드
        loadGradeInfo(food.food_id, foodCard.querySelector('.brand-tag'));
        
        // 좋아요 상태 초기화
        initializeFavoriteState(favoriteBtn, food.is_favorite);
    });
    
    searchResults.style.display = 'block';
}

// 검색 결과 없음 표시
function displayNoResults() {
    const searchResults = document.getElementById('searchResults');
    const searchResultsList = document.getElementById('searchResultsList');
    
    searchResultsList.innerHTML = '<div class="no-results">검색 결과가 없습니다.</div>';
    searchResults.style.display = 'block';
}

// 좋아요 토글 함수
async function toggleFavorite(button) {
    const productId = button.getAttribute('data-product-id');
    if (!productId) return;

    button.disabled = true;
    try {
        const res = await fetch(`/products/${productId}/like/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });
        if (!res.ok) throw new Error('네트워크 오류');

        const data = await res.json();
        if (data.is_favorite) {
            button.classList.add('active');
            button.setAttribute('data-is-favorite', 'true');
            button.setAttribute('aria-pressed', 'true');
        } else {
            button.classList.remove('active');
            button.setAttribute('data-is-favorite', 'false');
            button.setAttribute('aria-pressed', 'false');
        }
    } catch (e) {
        console.error('좋아요 처리 오류:', e);
    } finally {
        button.disabled = false;
    }
}

// 등급 정보 로드 함수
async function loadGradeInfo(productId, brandTag) {
    if (!brandTag) return;
    
    try {
        const res = await fetch(`/products/${productId}/?format=json`, { credentials: 'same-origin' });
        if (!res.ok) return;
        const product = await res.json();

        // letter_grade가 있으면 brand-tag 업데이트
        if (product.letter_grade) {
            brandTag.textContent = product.letter_grade;
            brandTag.className = 'brand-tag';
        }
    } catch (e) {
        console.error('등급 정보를 불러오는 중 오류:', e);
    }
}

// 좋아요 상태 초기화 함수
function initializeFavoriteState(button, isFavorite) {
    if (!button) return;
    
    if (isFavorite) {
        button.classList.add('active');
        button.setAttribute('data-is-favorite', 'true');
        button.setAttribute('aria-pressed', 'true');
    } else {
        button.classList.remove('active');
        button.setAttribute('data-is-favorite', 'false');
        button.setAttribute('aria-pressed', 'false');
    }
}

// 로딩 인디케이터 표시
function showLoadingIndicator() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'flex';
    }
}

// 로딩 인디케이터 숨김
function hideLoadingIndicator() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
    }
}

// 더보기 버튼 표시
function showLoadMoreButton() {
    const loadMoreContainer = document.getElementById('loadMoreContainer');
    if (loadMoreContainer) {
        loadMoreContainer.style.display = 'flex';
        console.log('더보기 버튼이 표시되었습니다.');
    }
}

// 더보기 버튼 숨김
function hideLoadMoreButton() {
    const loadMoreContainer = document.getElementById('loadMoreContainer');
    if (loadMoreContainer) {
        loadMoreContainer.style.display = 'none';
        console.log('더보기 버튼이 숨겨졌습니다.');
    }
}

function clearSearch() {
    // 검색 상태 초기화
    currentPage = 1;
    isLoading = false;
    hasMoreData = true;
    currentSearchKeyword = '';
    
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    const loadingIndicator = document.getElementById('loadingIndicator');
    
    if (searchInput) {
        searchInput.value = '';
    }
    
    if (searchResults) {
        searchResults.style.display = 'none';
    }
    
    if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
    }
    
    hideLoadMoreButton();
    
    // search_before 페이지로 이동
    window.location.href = '/search/';
}

// DOM 로드 완료 후 이벤트 리스너 등록
document.addEventListener('DOMContentLoaded', function() {
    // Enter 키로도 검색 가능하도록
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
    

    
    // 기존 food-card에 이벤트 리스너 추가
    const existingFoodCards = document.querySelectorAll('.food-card');
    existingFoodCards.forEach(card => {
        // 카드 클릭 이벤트
        card.addEventListener('click', function(e) {
            if (e.target.closest('.favorite-btn')) return;
            const foodId = card.getAttribute('data-food-id');
            if (foodId) {
                window.location.href = `/products/${foodId}`;
            }
        });
        
        // 좋아요 버튼 이벤트
        const favoriteBtn = card.querySelector('.favorite-btn');
        if (favoriteBtn) {
            favoriteBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                toggleFavorite(favoriteBtn);
            });
        }
        
        // 등급 정보 로드
        const foodId = card.getAttribute('data-food-id');
        const brandTag = card.querySelector('.brand-tag');
        if (foodId && brandTag) {
            loadGradeInfo(foodId, brandTag);
        }
        
        // 좋아요 상태 초기화
        if (favoriteBtn) {
            const isFavorite = favoriteBtn.getAttribute('data-is-favorite') === 'true';
            initializeFavoriteState(favoriteBtn, isFavorite);
        }
    });
});