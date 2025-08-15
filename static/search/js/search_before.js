// CSRF 토큰 가져오기
const getCookie = (name) => {
    const m = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[2]) : '';
};

const getCsrfToken = () => getCookie('csrftoken');

// 검색 페이지로 이동
function goToSearchPage() {
    window.location.href = '/search/page/';
}

// 메인 페이지로 이동
function goToMainPage() {
    window.location.href = '/';
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

// DOM 로드 완료 후 이벤트 리스너 등록
document.addEventListener('DOMContentLoaded', function() {
    // 좋아요 버튼 이벤트 리스너 추가
    const favoriteBtns = document.querySelectorAll('.favorite-btn');
    favoriteBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleFavorite(btn);
        });
    });

    // 카드 클릭 이벤트 (상세 페이지로 이동)
    const foodCards = document.querySelectorAll('.food-card');
    foodCards.forEach(card => {
        card.addEventListener('click', function(e) {
            // 버튼 클릭 시는 이동 막기
            if (e.target.closest('.favorite-btn')) return;
            
            const foodId = card.getAttribute('data-food-id');
            if (foodId) {
                window.location.href = `/products/${foodId}`;
            }
        });
    });

    // 등급 정보 로드
    foodCards.forEach(card => {
        const foodId = card.getAttribute('data-food-id');
        const brandTag = card.querySelector('.brand-tag');
        const favoriteBtn = card.querySelector('.favorite-btn');
        
        if (foodId && brandTag) {
            loadGradeInfo(foodId, brandTag);
        }
        
        if (favoriteBtn) {
            const isFavorite = favoriteBtn.getAttribute('data-is-favorite') === 'true';
            initializeFavoriteState(favoriteBtn, isFavorite);
        }
    });
});
