// 고급검색 페이지 JavaScript
class AdvancedSearchPage {
    constructor() {
      this.favorites = this.loadFavorites();
      this.currentPage = 1;
      this.hasMoreData = true;
      this.isLoading = false;
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

    // 더 많은 제품 로드
    async loadMoreProducts() {
      if (this.isLoading || !this.hasMoreData) return;
      
      this.isLoading = true;
      this.showLoading();
      
      try {
        const response = await fetch(`/search/advanced/?page=${this.currentPage + 1}&limit=4`, {
          method: 'GET',
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        });
        
        if (!response.ok) {
          throw new Error('제품 로드 실패');
        }
        
        const data = await response.json();
        
        if (data.foods && data.foods.length > 0) {
          this.displayMoreProducts(data.foods);
          this.currentPage++;
          
          if (!data.has_more) {
            this.hasMoreData = false;
            this.hideLoadMoreCard();
          }
        } else {
          this.hasMoreData = false;
          this.hideLoadMoreCard();
        }
      } catch (error) {
        console.error('제품 로드 오류:', error);
        alert('제품을 불러오는 중 오류가 발생했습니다.');
      } finally {
        this.isLoading = false;
        this.hideLoading();
      }
    }

    // 더 많은 제품 표시
    displayMoreProducts(foods) {
      const productList = document.getElementById('productList');
      const loadMoreCard = productList.querySelector('.additional-card');
      
      foods.forEach(food => {
        const productCard = this.createProductCard(food);
        productList.insertBefore(productCard, loadMoreCard);
      });
      
      // 새로운 제품들의 이벤트 리스너 바인딩
      this.bindEvents();
    }

    // 제품 카드 생성
    createProductCard(food) {
      const productCard = document.createElement('div');
      productCard.className = 'product-card';
      productCard.dataset.productId = food.food_id;
      
      productCard.innerHTML = `
        <img src="${food.food_img || ''}" alt="${food.food_name}" class="product-image">
        <div class="product-info">
          <h4 class="product-name clickable" data-product-id="${food.food_id}">${food.food_name}</h4>
          <p class="product-manufacturer">제조사: ${food.company_name || '제조사 정보 없음'}</p>
        </div>
        <button class="favorite-btn" data-product-id="${food.food_id}" data-is-favorite="false" type="button" aria-pressed="false" aria-label="즐겨찾기">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
            <path class="heart-path" d="M20.84 4.61C20.3292 4.099 19.7228 3.69364 19.0554 3.41708C18.3879 3.14052 17.6725 2.99817 16.95 2.99817C16.2275 2.99817 15.5121 3.14052 14.8446 3.41708C14.1772 3.69364 13.5708 4.099 13.06 4.61L12 5.67L10.94 4.61C9.9083 3.5783 8.50903 2.9987 7.05 2.9987C5.59096 2.9987 4.19169 3.5783 3.16 4.61C2.1283 5.6417 1.5487 7.04097 1.5487 8.5C1.5487 9.95903 2.1283 11.3583 3.16 12.39L12 21.23L20.84 12.39C21.351 11.8792 21.7564 11.2728 22.0329 10.6054C22.3095 9.93789 22.4518 9.22249 22.4518 8.5C22.4518 7.77751 22.3095 7.0621 22.0329 6.39464C21.7564 5.72718 21.351 5.12075 20.84 4.61Z"/>
          </svg>
        </button>
      `;
      
      return productCard;
    }

    // 로딩 표시
    showLoading() {
      const loadingIndicator = document.getElementById('loadingIndicator');
      if (loadingIndicator) {
        loadingIndicator.style.display = 'block';
      }
    }

    // 로딩 숨기기
    hideLoading() {
      const loadingIndicator = document.getElementById('loadingIndicator');
      if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
      }
    }

    // 더보기 카드 숨기기
    hideLoadMoreCard() {
      const loadMoreCard = document.querySelector('.additional-card');
      if (loadMoreCard) {
        loadMoreCard.style.display = 'none';
      }
    }
  
    // 즐겨찾기 토글
    // async toggleFavorite(favoriteBtn) {
    //   const productId = favoriteBtn.getAttribute('data-product-id');
    //   if (!productId) return;
  
    //   favoriteBtn.disabled = true;
      
    //   try {
    //     const response = await fetch(`/products/${productId}/like/`, {
    //       method: 'POST',
    //       headers: {
    //         'Content-Type': 'application/json',
    //         'X-CSRFToken': this.getCsrfToken(),
    //         'X-Requested-With': 'XMLHttpRequest'
    //       },
    //       credentials: 'same-origin'
    //     });
  
    //     if (!response.ok) {
    //       throw new Error('네트워크 오류');
    //     }
  
    //     const data = await response.json();
    //     const isFavorite = data.is_favorite;

    //     // 로컬 상태 업데이트
    //     if (isFavorite) {
    //       this.favorites[productId] = true;
    //     } else {
    //       delete this.favorites[productId];
    //     }
    //     this.saveFavorites();

    //     favoriteBtn.classList.toggle('active', isFavorite);
    //     favoriteBtn.setAttribute('data-is-favorite', String(isFavorite));
    //     favoriteBtn.setAttribute('aria-pressed', String(isFavorite));
    //   } catch (error) {
    //     console.error('찜 처리 오류:', error);
    //   } finally {
    //     favoriteBtn.disabled = false;
    //   }
    // }

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

        // 상태 반영
        if (isFavorite) {
          this.favorites[productId] = true;
        } else {
          delete this.favorites[productId];
        }
        this.saveFavorites();

        // 버튼 스타일 변경
        favoriteBtn.classList.toggle('active', isFavorite);
        favoriteBtn.setAttribute('data-is-favorite', String(isFavorite));
        favoriteBtn.setAttribute('aria-pressed', String(isFavorite));

        // 하트 아이콘 색상 변경 (필요 시)
        const heartPath = favoriteBtn.querySelector('.heart-path');
        if (heartPath) {
          heartPath.setAttribute('fill', isFavorite ? '#FF4081' : 'none');
        }

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

// 더 많은 제품을 로드하는 전역 함수
function loadMoreProducts() {
  if (window.advancedSearch) {
    window.advancedSearch.loadMoreProducts();
  }
}

// 홈페이지로 이동하는 전역 함수
function goToHome() {
  window.location.href = '/';
}