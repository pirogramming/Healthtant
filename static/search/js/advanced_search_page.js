// 고급검색 페이지 JavaScript
class AdvancedSearchPage {
    constructor() {
      this.favorites = this.loadFavorites();
      this.init();
    }
  
    init() {
      console.log('AdvancedSearchPage 초기화 시작');
      this.addStyles();
      this.bindEvents();
      this.updateFavoriteButtons();
      console.log('AdvancedSearchPage 초기화 완료');
    }

    // 로컬스토리지에서 좋아요 상태 로드
    loadFavorites() {
      const stored = localStorage.getItem('healthtant_favorites');
      return stored ? JSON.parse(stored) : {};
    }

    // 로컬스토리지에 좋아요 상태 저장
    saveFavorites() {
      localStorage.setItem('healthtant_favorites', JSON.stringify(this.favorites));
    }

    // 좋아요 버튼 상태 업데이트
    updateFavoriteButtons() {
      const favoriteBtns = document.querySelectorAll('.favorite-btn');
      favoriteBtns.forEach(btn => {
        const productId = btn.getAttribute('data-product-id');
        if (productId && this.favorites[productId]) {
          btn.classList.add('active');
          btn.setAttribute('data-is-favorite', 'true');
          btn.setAttribute('aria-pressed', 'true');
        }
      });
    }
  
    bindEvents() {
      console.log('bindEvents 시작');
      
      // 검색하기 버튼 이벤트 리스너
      const searchBtn = document.getElementById('searchBtn');
      const searchInput = document.getElementById('searchInput');
      
      if (searchBtn && searchInput) {
        searchBtn.addEventListener('click', () => {
          this.performSearch();
        });
        
        // 엔터키로도 검색 가능하도록
        searchInput.addEventListener('keypress', (e) => {
          if (e.key === 'Enter') {
            this.performSearch();
          }
        });
      }
  
      // 즐겨찾기 버튼 이벤트 리스너
      const favoriteBtns = document.querySelectorAll('.favorite-btn');
      favoriteBtns.forEach(favoriteBtn => {
        favoriteBtn.addEventListener('click', (e) => {
          e.preventDefault();
          this.toggleFavorite(favoriteBtn);
        });
      });

      // 상품 제목 클릭 이벤트 리스너
      console.log('상품 제목 클릭 이벤트 바인딩 시작');
      this.bindProductTitleClicks();
      console.log('bindEvents 완료');
    }

    // 상품 제목 클릭 이벤트 바인딩
    bindProductTitleClicks() {
      console.log('상품 제목 클릭 이벤트 바인딩 시작');
      
      // 추천 상품 제목들 - HTML 구조에 맞게 수정
      const productTitles = document.querySelectorAll('.product-name.clickable');
      console.log('찾은 상품 제목 요소들:', productTitles);
      
      productTitles.forEach((title, index) => {
        console.log(`상품 제목 ${index + 1}:`, title.textContent, title);
        title.style.cursor = 'pointer';
        title.addEventListener('click', (e) => {
          console.log('상품 제목 클릭됨:', title.textContent);
          e.preventDefault();
          this.goToProductDetail(title);
        });
      });
      
      console.log('상품 제목 클릭 이벤트 바인딩 완료');
    }

    // 상품 상세 페이지로 이동
    goToProductDetail(titleElement) {
      console.log('goToProductDetail 호출됨:', titleElement);
      
      // 상품 ID를 찾는 방법들
      let productId = null;
      
      // data-product-id 속성 확인
      if (titleElement.dataset.productId) {
        productId = titleElement.dataset.productId;
        console.log('titleElement에서 직접 찾음:', productId);
      }
      // 부모 요소에서 확인
      else if (titleElement.closest('[data-product-id]')) {
        productId = titleElement.closest('[data-product-id]').dataset.productId;
        console.log('부모 요소에서 찾음:', productId);
      }
      // 부모 요소에서 확인 (food-id)
      else if (titleElement.closest('[data-food-id]')) {
        productId = titleElement.closest('[data-food-id]').dataset.foodId;
        console.log('food-id에서 찾음:', productId);
      }
      
      console.log('최종 productId:', productId);
      
      if (productId) {
        console.log(`상품 상세 페이지로 이동: /products/${productId}/`);
        window.location.href = `/products/${productId}/`;
      } else {
        console.error('상품 ID를 찾을 수 없습니다.');
      }
    }
  
    // 검색 실행
    performSearch() {
      const searchInput = document.getElementById('searchInput');
      const keyword = searchInput.value.trim();
      
      if (keyword) {
        // 좋아요 상태를 URL 파라미터로 전달
        const favoritesParam = encodeURIComponent(JSON.stringify(this.favorites));
        window.location.href = `/search/advanced/?keyword=${encodeURIComponent(keyword)}&favorites=${favoritesParam}`;
      } else {
        alert('검색어를 입력해주세요.');
      }
    }
  
    // 즐겨찾기 토글
    async toggleFavorite(favoriteBtn) {
      const productId = favoriteBtn.getAttribute('data-product-id');
      if (!productId) return;
  
      favoriteBtn.disabled = true;
      
      try {
        const response = await fetch(`/products/${productId}/like/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest'
          },
          credentials: 'same-origin'
        });
  
        if (!response.ok) {
          throw new Error('네트워크 오류');
        }
  
        const data = await response.json();
        const isFavorite = data.is_favorite;

        // 로컬 상태 업데이트
        if (isFavorite) {
          this.favorites[productId] = true;
        } else {
          delete this.favorites[productId];
        }
        this.saveFavorites();

        favoriteBtn.classList.toggle('active', isFavorite);
        favoriteBtn.setAttribute('data-is-favorite', String(isFavorite));
        favoriteBtn.setAttribute('aria-pressed', String(isFavorite));
      } catch (error) {
        console.error('찜 처리 오류:', error);
      } finally {
        favoriteBtn.disabled = false;
      }
    }
  
    // CSRF 토큰 가져오기
    getCsrfToken() {
      const input = document.querySelector('[name=csrfmiddlewaretoken]');
      const meta = document.querySelector('meta[name="csrf-token"]');
      return (input && input.value) || (meta && meta.content) || '';
    }

    // CSS 스타일 추가
    addStyles() {
      const style = document.createElement('style');
      style.textContent = `
        /* 클릭 가능한 상품 제목 스타일 */
        .product-name.clickable {
          cursor: pointer;
          transition: color 0.2s ease;
        }

        .product-name.clickable:hover {
          color: #56AAB2;
          text-decoration: underline;
        }

        .product-name.clickable:active {
          color: #4a959c;
        }
      `;
      document.head.appendChild(style);
    }
}
  
  // 페이지 로드 시 초기화
  document.addEventListener('DOMContentLoaded', () => {
    window.advancedSearch = new AdvancedSearchPage();
  });