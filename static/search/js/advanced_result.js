// 고급검색 결과 페이지 JavaScript
class AdvancedResultPage {
  constructor() {
    this.currentPage = 1;
    this.searchToken = null;
    this.currentKeyword = '';
    this.currentOrder = '';
    this.currentFilters = {};
    this.isLoading = false;
    this.currentFavorites = {};
    
    this.init();
  }

  init() {
    this.bindEvents();
    this.loadInitialResults();
  }

  bindEvents() {
    // 검색 입력 필드
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    
    if (searchInput) {
      searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          this.performSearch();
        }
      });
    }
    
    // 검색 버튼 클릭 이벤트
    if (searchButton) {
      searchButton.addEventListener('click', () => {
        this.performSearch();
      });
    }

    // 정렬 드롭다운
    const sortDropdown = document.getElementById('sortDropdown');
    if (sortDropdown) {
      sortDropdown.addEventListener('click', () => this.toggleSortModal());
    }

    // 필터 버튼
    const filterButton = document.getElementById('filterButton');
    if (filterButton) {
      filterButton.addEventListener('click', () => this.toggleFilterModal());
    }

    // 모달 닫기 버튼들
    const closeSortModal = document.getElementById('closeSortModal');
    if (closeSortModal) {
      closeSortModal.addEventListener('click', () => this.hideSortModal());
    }

    const closeFilterModal = document.getElementById('closeFilterModal');
    if (closeFilterModal) {
      closeFilterModal.addEventListener('click', () => this.hideFilterModal());
    }

    // 정렬 옵션들
    const sortOptions = document.querySelectorAll('.sort-option');
    sortOptions.forEach(option => {
      option.addEventListener('click', () => this.selectSort(option.dataset.order));
    });

    // 필터 적용/초기화
    const applyFilter = document.getElementById('applyFilter');
    if (applyFilter) {
      applyFilter.addEventListener('click', () => this.applyFilters());
    }

    const resetFilter = document.getElementById('resetFilter');
    if (resetFilter) {
      resetFilter.addEventListener('click', () => this.resetFilters());
    }

    // 홈 아이콘 클릭
    const homeIcon = document.querySelector('.home-icon');
    if (homeIcon) {
      homeIcon.addEventListener('click', () => {
        window.location.href = '/';
      });
    }

    // 모달 외부 클릭 시 닫기
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('sort-modal') || e.target.classList.contains('filter-modal')) {
        this.hideSortModal();
        this.hideFilterModal();
      }
    });
  }

  // 초기 결과 로드
  async loadInitialResults() {
    const urlParams = new URLSearchParams(window.location.search);
    const keyword = urlParams.get('keyword') || '';
    const favoritesParam = urlParams.get('favorites') || '';
    
    // URL에서 좋아요 상태 복원
    if (favoritesParam) {
      try {
        const favorites = JSON.parse(decodeURIComponent(favoritesParam));
        this.restoreFavorites(favorites);
      } catch (error) {
        console.error('좋아요 상태 복원 오류:', error);
      }
    } else {
      // URL 파라미터가 없으면 로컬스토리지에서 로드
      this.loadFavoritesFromStorage();
    }
    
    if (keyword) {
      this.currentKeyword = keyword;
      await this.searchFoods(keyword);
    } else {
      this.showNoResults();
    }
  }

  // 로컬스토리지에서 좋아요 상태 로드
  loadFavoritesFromStorage() {
    try {
      const stored = localStorage.getItem('healthtant_favorites');
      if (stored) {
        const favorites = JSON.parse(stored);
        this.currentFavorites = favorites;
      }
    } catch (error) {
      console.error('로컬스토리지에서 좋아요 상태 로드 오류:', error);
      this.currentFavorites = {};
    }
  }

  // 좋아요 상태 복원
  restoreFavorites(favorites) {
    this.currentFavorites = favorites;
    // 로컬스토리지에도 저장
    localStorage.setItem('healthtant_favorites', JSON.stringify(favorites));
  }

  // 현재 좋아요 상태 확인
  isFavorite(foodId) {
    return this.currentFavorites && this.currentFavorites[foodId] === true;
  }

  // 검색 실행
  async performSearch() {
    const searchInput = document.getElementById('searchInput');
    const keyword = searchInput.value.trim();
    
    if (!keyword) {
      this.showToast('검색어를 입력해주세요.');
      return;
    }

    this.currentKeyword = keyword;
    this.currentPage = 1;
    await this.searchFoods(keyword);
  }

  // 음식 검색 API 호출
  async searchFoods(keyword) {
    this.showLoading();
    
    try {
      const params = new URLSearchParams({
        keyword: keyword,
        page: this.currentPage
      });

      const response = await fetch(`/search/advanced/?${params}`, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      });

      if (!response.ok) {
        throw new Error('검색 요청 실패');
      }

      const data = await response.json();
      this.handleSearchResponse(data);
    } catch (error) {
      console.error('검색 오류:', error);
      this.showToast('검색 중 오류가 발생했습니다.');
      this.hideLoading();
    }
  }

  // 검색 결과 처리
  handleSearchResponse(data) {
    this.searchToken = data.search_token;
    this.currentKeyword = data.keyword;
    
    if (data.foods && data.foods.length > 0) {
      // 서버에서 받은 좋아요 상태와 로컬 상태 병합
      this.mergeFavoriteStates(data.foods);
      this.displayFoods(data.foods);
      this.displayPagination(data.page, data.total_pages, data.total);
    } else {
      this.showNoResults();
    }
    
    this.hideLoading();
  }

  // 서버 데이터와 로컬 좋아요 상태 병합
  mergeFavoriteStates(foods) {
    foods.forEach(food => {
      // 서버에서 받은 상태가 있으면 우선, 없으면 로컬 상태 사용
      if (food.is_favorite !== undefined) {
        this.currentFavorites[food.food_id] = food.is_favorite;
      }
    });
    
    // 로컬스토리지 업데이트
    localStorage.setItem('healthtant_favorites', JSON.stringify(this.currentFavorites));
  }

  // 음식 목록 표시
  displayFoods(foods) {
    const resultList = document.getElementById('resultList');
    if (!resultList) return;

    resultList.innerHTML = '';
    
    foods.forEach(food => {
      const foodElement = this.createFoodElement(food);
      resultList.appendChild(foodElement);
    });
  }

  // 음식 요소 생성
  createFoodElement(food) {
    const foodDiv = document.createElement('div');
    foodDiv.className = 'food-item';
    foodDiv.dataset.foodId = food.food_id;

    // 서버 상태와 로컬 상태를 모두 확인
    const serverFavorite = food.is_favorite === true;
    const localFavorite = this.isFavorite(food.food_id);
    const isFavorite = serverFavorite || localFavorite;
    
    const favoriteClass = isFavorite ? 'active' : '';
    const svgFill = isFavorite ? 'currentColor' : 'none';

    foodDiv.innerHTML = `
      <div class="food-image">
        ${food.image ? `<img src="${food.image}" alt="${food.food_name}">` : '이미지 없음'}
      </div>
      <div class="food-info">
        <div class="food-name clickable" onclick="advancedResult.goToProductDetail('${food.food_id}')">${food.food_name}</div>
        <div class="food-company">${food.company_name || '제조사 정보 없음'}</div>
      </div>
      <button class="favorite-button ${favoriteClass}" 
              onclick="advancedResult.toggleFavorite('${food.food_id}')">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="${svgFill}">
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" 
                stroke="currentColor" stroke-width="2" fill-rule="evenodd"/>
        </svg>
      </button>
    `;

    return foodDiv;
  }

  // 페이지네이션 표시
  displayPagination(currentPage, totalPages, total) {
    const pagination = document.getElementById('pagination');
    if (!pagination) return;

    if (totalPages <= 1) {
      pagination.style.display = 'none';
      return;
    }

    pagination.style.display = 'flex';
    
    // 이전/다음 버튼
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    
    if (prevBtn) prevBtn.disabled = currentPage <= 1;
    if (nextBtn) nextBtn.disabled = currentPage >= totalPages;

    // 페이지 번호들
    const pageNumbers = document.getElementById('pageNumbers');
    if (pageNumbers) {
      pageNumbers.innerHTML = '';
      
      const startPage = Math.max(1, currentPage - 2);
      const endPage = Math.min(totalPages, currentPage + 2);
      
      for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('div');
        pageBtn.className = `page-number ${i === currentPage ? 'active' : ''}`;
        pageBtn.textContent = i;
        pageBtn.addEventListener('click', () => this.goToPage(i));
        pageNumbers.appendChild(pageBtn);
      }
    }

    // 이전/다음 버튼 이벤트
    if (prevBtn) {
      prevBtn.onclick = () => this.goToPage(currentPage - 1);
    }
    if (nextBtn) {
      nextBtn.onclick = () => this.goToPage(currentPage + 1);
    }
  }

  // 특정 페이지로 이동
  async goToPage(page) {
    if (page < 1 || this.isLoading) return;
    
    this.currentPage = page;
    await this.refineSearch();
  }

  // 정렬 선택
  async selectSort(order) {
    this.currentOrder = order;
    this.currentPage = 1;
    this.hideSortModal();
    await this.refineSearch();
  }

  // 필터 적용
  async applyFilters() {
    this.currentFilters = this.getFilterValues();
    this.currentPage = 1;
    this.hideFilterModal();
    await this.refineSearch();
  }

  // 필터 값 가져오기
  getFilterValues() {
    const filters = {};
    const filterFields = ['calorie', 'protein', 'fat', 'carb', 'salt', 'sugar'];
    
    filterFields.forEach(field => {
      const min = document.getElementById(`${field}Min`);
      const max = document.getElementById(`${field}Max`);
      
      if (min && min.value) filters[`${field}_min`] = parseFloat(min.value);
      if (max && max.value) filters[`${field}_max`] = parseFloat(max.value);
    });
    
    return filters;
  }

  // 필터 초기화
  resetFilters() {
    const filterInputs = document.querySelectorAll('.filter-options input');
    filterInputs.forEach(input => input.value = '');
    
    this.currentFilters = {};
    this.currentPage = 1;
    this.refineSearch();
  }

  // 세밀 검색 실행
  async refineSearch() {
    if (!this.searchToken) {
      await this.searchFoods(this.currentKeyword);
      return;
    }

    this.showLoading();
    
    try {
      const params = new URLSearchParams({
        token: this.searchToken,
        page: this.currentPage,
        size: 30
      });

      if (this.currentOrder) {
        params.append('order', this.currentOrder);
      }

      if (this.currentKeyword) {
        params.append('keyword', this.currentKeyword);
      }

      // 필터 파라미터 추가
      Object.entries(this.currentFilters).forEach(([key, value]) => {
        params.append(key, value);
      });

      const response = await fetch(`/search/refine/?${params}`, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      });

      if (!response.ok) {
        throw new Error('세밀 검색 요청 실패');
      }

      const data = await response.json();
      this.handleSearchResponse(data);
    } catch (error) {
      console.error('세밀 검색 오류:', error);
      this.showToast('검색 중 오류가 발생했습니다.');
      this.hideLoading();
    }
  }

  // 즐겨찾기 토글
  async toggleFavorite(foodId) {
    try {
      const response = await fetch(`/products/${foodId}/like/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest'
        }
      });

      if (!response.ok) {
        throw new Error('즐겨찾기 처리 실패');
      }

      const data = await response.json();
      
      // 로컬 상태 업데이트
      if (data.is_favorite) {
        this.currentFavorites[foodId] = true;
      } else {
        delete this.currentFavorites[foodId];
      }
      localStorage.setItem('healthtant_favorites', JSON.stringify(this.currentFavorites));
      
      // UI 업데이트
      const favoriteBtn = document.querySelector(`[data-food-id="${foodId}"] .favorite-button`);
      
      if (favoriteBtn) {
        favoriteBtn.classList.toggle('active', data.is_favorite);
        const svg = favoriteBtn.querySelector('svg');
        if (svg) {
          svg.setAttribute('fill', data.is_favorite ? 'currentColor' : 'none');
        }
      }

      // 다른 페이지와의 동기화를 위한 이벤트 발생
      window.dispatchEvent(new CustomEvent('favoriteChanged', {
        detail: { foodId, isFavorite: data.is_favorite }
      }));

      this.showToast(data.is_favorite ? '즐겨찾기에 추가되었습니다.' : '즐겨찾기에서 제거되었습니다.');
    } catch (error) {
      console.error('즐겨찾기 오류:', error);
      this.showToast('즐겨찾기 처리 중 오류가 발생했습니다.');
    }
  }

  // CSRF 토큰 가져오기
  getCsrfToken() {
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    const meta = document.querySelector('meta[name="csrf-token"]');
    return (input && input.value) || (meta && meta.content) || '';
  }

  // 정렬 모달 토글
  toggleSortModal() {
    const sortModal = document.getElementById('sortModal');
    if (sortModal) {
      sortModal.classList.toggle('show');
    }
  }

  // 정렬 모달 숨기기
  hideSortModal() {
    const sortModal = document.getElementById('sortModal');
    if (sortModal) {
      sortModal.classList.remove('show');
    }
  }

  // 필터 모달 토글
  toggleFilterModal() {
    const filterModal = document.getElementById('filterModal');
    if (filterModal) {
      filterModal.classList.toggle('show');
    }
  }

  // 필터 모달 숨기기
  hideFilterModal() {
    const filterModal = document.getElementById('filterModal');
    if (filterModal) {
      filterModal.classList.remove('show');
    }
  }

  // 로딩 표시
  showLoading() {
    this.isLoading = true;
    const loadingState = document.getElementById('loadingState');
    if (loadingState) {
      loadingState.style.display = 'block';
    }
    
    const resultList = document.getElementById('resultList');
    if (resultList) {
      resultList.style.display = 'none';
    }
  }

  // 로딩 숨기기
  hideLoading() {
    this.isLoading = false;
    const loadingState = document.getElementById('loadingState');
    if (loadingState) {
      loadingState.style.display = 'none';
    }
    
    const resultList = document.getElementById('resultList');
    if (resultList) {
      resultList.style.display = 'block';
    }
  }

  // 검색 결과 없음 표시
  showNoResults() {
    const noResults = document.getElementById('noResults');
    if (noResults) {
      noResults.style.display = 'block';
    }
    
    const resultList = document.getElementById('resultList');
    if (resultList) {
      resultList.style.display = 'none';
    }
    
    const pagination = document.getElementById('pagination');
    if (pagination) {
      pagination.style.display = 'none';
    }
  }

  // 토스트 메시지 표시
  showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%);
      background: #333;
      color: white;
      padding: 12px 24px;
      border-radius: 24px;
      font-size: 14px;
      z-index: 1000;
      animation: slideUp 0.3s ease-out;
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'slideDown 0.3s ease-out';
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 300);
    }, 3000);
  }

  // 상품 상세 페이지로 이동
  goToProductDetail(foodId) {
    window.location.href = `/products/${foodId}/`;
  }
}

// CSS 애니메이션 추가
const style = document.createElement('style');
style.textContent = `
  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translate(-50%, 20px);
    }
    to {
      opacity: 1;
      transform: translate(-50%, 0);
    }
  }
  
  @keyframes slideDown {
    from {
      opacity: 1;
      transform: translate(-50%, 0);
    }
    to {
      opacity: 0;
      transform: translate(-50%, 20px);
    }
  }

  /* 클릭 가능한 상품 제목 스타일 */
  .food-name.clickable {
    cursor: pointer;
    transition: color 0.2s ease;
  }

  .food-name.clickable:hover {
    color: #56AAAB;
    text-decoration: underline;
  }

  .food-name.clickable:active {
    color: #56AAAB;
  }
`;
document.head.appendChild(style);

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
  window.advancedResult = new AdvancedResultPage();
});
