// 고급검색 페이지 JavaScript
class AdvancedSearchPage {
    constructor() {
      this.init();
    }
  
    init() {
      this.bindEvents();
    }
  
    bindEvents() {
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
    }
  
    // 검색 실행
    performSearch() {
      const searchInput = document.getElementById('searchInput');
      const keyword = searchInput.value.trim();
      
      if (keyword) {
        // 검색어와 함께 결과 페이지로 이동
        window.location.href = `/search/advanced/?keyword=${encodeURIComponent(keyword)}`;
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
  }
  
  // 페이지 로드 시 초기화
  document.addEventListener('DOMContentLoaded', () => {
    window.advancedSearch = new AdvancedSearchPage();
  });