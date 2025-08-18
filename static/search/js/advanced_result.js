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
    
    // 페이지네이션 관련 변수 추가
    this.hasMoreData = true;
    this.ITEMS_PER_PAGE = 30;
    
    // 원본 음식 데이터 캐시 추가
    this.cachedFoods = [];
    
    this.init();
  }

  init() {
    this.bindEvents();
    this.loadInitialResults();
    this.updateFavoriteButtons();
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
    const orderParam = urlParams.get('order') || '';
    
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
    
    // 정렬 상태 복원
    if (orderParam) {
      this.currentOrder = orderParam;
      this.updateSortLabel(orderParam);
      this.updateSortOptionStates(orderParam);
    } else {
      // 정렬 파라미터가 없으면 기본순으로 설정
      this.currentOrder = '';
      this.updateSortLabel('정렬');
      this.updateSortOptionStates('');
    }
    
    if (keyword) {
      this.currentKeyword = keyword;
      await this.searchFoods(keyword);
    } else {
      this.showNoResults();
    }
    
    // 즐겨찾기 버튼 상태 업데이트
    this.updateFavoriteButtons();
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

  // 좋아요 버튼 상태 업데이트
  updateFavoriteButtons() {
    const favoriteBtns = document.querySelectorAll('.favorite-button');
    favoriteBtns.forEach(btn => {
      const productId = btn.getAttribute('data-product-id');
      if (productId && this.currentFavorites[productId]) {
        btn.classList.add('active');
        btn.setAttribute('data-is-favorite', 'true');
        btn.setAttribute('aria-pressed', 'true');
      }
    });
  }

  // 로컬스토리지에 좋아요 상태 저장
  saveFavorites() {
    localStorage.setItem('healthtant_favorites', JSON.stringify(this.currentFavorites));
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
    this.hasMoreData = true;
    
    // 검색 시 현재 정렬 상태를 URL에 포함
    const params = new URLSearchParams({
      keyword: keyword
    });
    
    if (this.currentOrder) {
      params.append('order', this.currentOrder);
    }
    
    // URL 업데이트
    const newUrl = `/search/advanced/?${params.toString()}`;
    window.history.pushState({}, '', newUrl);
    
    this.hideLoadMoreButton();
    await this.searchFoods(keyword);
  }

  // 더 많은 결과 로드 (페이지네이션)
  async loadMoreResults() {
    if (this.isLoading || !this.hasMoreData || !this.currentKeyword) return;
    
    console.log(`페이지 로드: ${this.currentPage}, 검색어: ${this.currentKeyword}`);
    
    this.isLoading = true;
    this.showLoading();
    this.hideLoadMoreButton();
    
    try {
      const params = new URLSearchParams({
        keyword: this.currentKeyword,
        page: this.currentPage,
        limit: this.ITEMS_PER_PAGE
      });
      
      // 정렬과 필터 파라미터 추가
      if (this.currentOrder) {
        params.append('order', this.currentOrder);
      }
      
      if (Object.keys(this.currentFilters).length > 0) {
        Object.entries(this.currentFilters).forEach(([key, value]) => {
          if (value !== null && value !== '') {
            params.append(key, value);
          }
        });
      }
      
      const response = await fetch(`/search/advanced/?${params.toString()}`, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      });
      const data = await response.json();
      
      console.log(`받은 데이터: ${data.foods.length}개 제품`);
      
      if (data.foods.length === 0) {
        this.hasMoreData = false;
        console.log('더 이상 데이터가 없습니다.');
        if (this.currentPage === 1) {
          this.showNoResults();
        }
      } else {
        this.displaySearchResults(data.foods);
        
        // 더 이상 데이터가 없으면
        if (data.foods.length < this.ITEMS_PER_PAGE) {
          this.hasMoreData = false;
          console.log('마지막 페이지입니다.');
        } else {
          this.showLoadMoreButton();
          console.log('더보기 버튼을 표시합니다.');
        }
        
        this.currentPage++;
      }
    } catch (error) {
      console.error('검색 중 오류가 발생했습니다:', error);
      this.showToast('검색 중 오류가 발생했습니다.');
    } finally {
      this.isLoading = false;
      this.hideLoading();
    }
  }

  // 음식 검색 API 호출
  async searchFoods(keyword) {
    this.showLoading();
    
    try {
      const params = new URLSearchParams({
        keyword: keyword,
        page: this.currentPage,
        limit: this.ITEMS_PER_PAGE
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
      
      // 원본 데이터 캐시에 저장
      this.cachedFoods = [...data.foods];
      
      this.displayFoods(data.foods);
      
      // 더 이상 데이터가 없으면
      if (data.foods.length < this.ITEMS_PER_PAGE) {
        this.hasMoreData = false;
      } else {
        this.showLoadMoreButton();
      }
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
    
    // 즐겨찾기 버튼 상태 업데이트
    this.updateFavoriteButtons();
  }

  // 검색 결과 표시 (페이지네이션용)
  displaySearchResults(foods) {
    const resultList = document.getElementById('resultList');
    if (!resultList) return;

    // 첫 페이지가 아니면 기존 결과에 추가
    if (this.currentPage > 1) {
      // 기존 no-results 메시지 제거
      const noResults = resultList.querySelector('.no-results');
      if (noResults) {
        noResults.remove();
      }
      
      // 캐시된 데이터에 추가
      this.cachedFoods = [...this.cachedFoods, ...foods];
    }
    
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
    const dataIsFavorite = isFavorite ? 'true' : 'false';
    const ariaPressed = isFavorite ? 'true' : 'false';

    foodDiv.innerHTML = `
      <div class="food-image">
        ${food.food_img ? `<img src="${food.food_img}" alt="${food.food_name}">` : '이미지 없음'}
      </div>
      <div class="food-info">
        <div class="food-left">
          <span class="brand-tag">${food.nutri_score_grade || '등급 없음'}</span>
        </div>
        <div class="food-right">
          <div class="food-name clickable" onclick="advancedResult.goToProductDetail('${food.food_id}')">${food.food_name}</div>
          <div class="food-company">${food.company_name || '판매처 정보 없음'}</div>
        </div>
      </div>
      <button class="favorite-button ${favoriteClass}" 
              data-product-id="${food.food_id}" 
              data-is-favorite="${dataIsFavorite}" 
              type="button" 
              aria-pressed="${ariaPressed}" 
              aria-label="즐겨찾기">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
          <path class="heart-path" d="M20.84 4.61C20.3292 4.099 19.7228 3.69364 19.0554 3.41708C18.3879 3.14052 17.6725 2.99817 16.95 2.99817C16.2275 2.99817 15.5121 3.14052 14.8446 3.41708C14.1772 3.69364 13.5708 4.099 13.06 4.61L12 5.67L10.94 4.61C9.9083 3.5783 8.50903 2.9987 7.05 2.9987C5.59096 2.9987 4.19169 3.5783 3.16 4.61C2.1283 5.6417 1.5487 7.04097 1.5487 8.5C1.5487 9.95903 2.1283 11.3583 3.16 12.39L12 21.23L20.84 12.39C21.351 11.8792 21.7564 11.2728 22.0329 10.6054C22.3095 9.93789 22.4518 9.22249 22.4518 8.5C22.4518 7.77751 22.3095 7.0621 22.0329 6.39464C21.7564 5.72718 21.351 5.12075 20.84 4.61Z"/>
        </svg>
      </button>
    `;

    // 생성된 버튼에 이벤트 리스너 추가
    const favoriteBtn = foodDiv.querySelector('.favorite-button');
    if (favoriteBtn) {
      favoriteBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.toggleFavorite(favoriteBtn);
      });
    }

    return foodDiv;
  }



  // 정렬 선택
  async selectSort(order) {
    console.log('정렬 선택됨:', order);
    
    // 기본순인 경우 정렬 초기화
    if (order === '기본순') {
      this.resetSort();
      return;
    }
    
    this.currentOrder = order;
    this.currentPage = 1;
    this.hasMoreData = true;
    
    // 정렬 드롭다운 라벨 업데이트
    this.updateSortLabel(order);
    
    // 정렬 옵션 활성화 상태 업데이트
    this.updateSortOptionStates(order);
    
    // 사용자에게 정렬 적용 알림
    this.showToast(`"${order}" 순으로 정렬되었습니다.`);
    
    this.hideSortModal();
    
    // 더보기 버튼 숨기기
    this.hideLoadMoreButton();
    
    // 검색 결과가 이미 있는 경우 즉시 정렬 적용
    const resultList = document.getElementById('resultList');
    if (resultList && resultList.children.length > 0) {
      // 현재 표시된 음식들의 전체 데이터를 저장된 상태에서 가져오기
      const currentFoods = this.getCurrentDisplayedFoods();
      
      if (currentFoods.length > 0) {
        console.log('기존 데이터로 정렬 적용:', currentFoods.length);
        const sortedFoods = this.sortFoods(currentFoods, order);
        this.displayFoods(sortedFoods);
        
        // 정렬 후 더보기 버튼 표시 여부 결정
        if (sortedFoods.length >= this.ITEMS_PER_PAGE) {
          this.showLoadMoreButton();
        }
        return;
      }
    }
    
    // 검색 결과가 없거나 정렬할 수 없는 경우 새로 검색
    await this.refineSearch();
  }

  // 정렬 초기화
  resetSort() {
    console.log('정렬 초기화');
    this.currentOrder = '';
    this.currentPage = 1;
    this.hasMoreData = true;
    
    // 정렬 드롭다운 라벨 초기화
    this.updateSortLabel('정렬');
    
    // 정렬 옵션 활성화 상태 초기화
    this.updateSortOptionStates('');
    
    // 사용자에게 초기화 알림
    this.showToast('정렬이 초기화되었습니다.');
    
    this.hideSortModal();
    
    // 더보기 버튼 숨기기
    this.hideLoadMoreButton();
    
    // 검색 결과가 이미 있는 경우 원본 순서로 복원
    if (this.cachedFoods.length > 0) {
      console.log('원본 데이터 순서로 복원:', this.cachedFoods.length);
      
      // 필터만 적용하고 정렬은 하지 않음
      let filteredFoods = this.applyFiltersToFoods(this.cachedFoods);
      this.displayFoods(filteredFoods);
      
      // 더보기 버튼 표시 여부 결정
      if (filteredFoods.length >= this.ITEMS_PER_PAGE) {
        this.showLoadMoreButton();
      }
    }
  }

  // 현재 표시된 음식들의 전체 데이터 가져오기
  getCurrentDisplayedFoods() {
    const resultList = document.getElementById('resultList');
    if (!resultList) return [];
    
    const foods = [];
    const foodItems = resultList.querySelectorAll('.food-item');
    
    foodItems.forEach(item => {
      const foodId = item.dataset.foodId;
      const foodName = item.querySelector('.food-name')?.textContent || '';
      const companyName = item.querySelector('.food-company')?.textContent || '';
      const foodImage = item.querySelector('.food-image img')?.src || '';
      
      // 저장된 원본 데이터에서 찾기
      const originalFood = this.findOriginalFoodData(foodId);
      
      if (originalFood) {
        foods.push(originalFood);
      } else {
        // 원본 데이터가 없으면 기본 정보로 구성
        foods.push({
          food_id: foodId,
          food_name: foodName,
          company_name: companyName,
          food_img: foodImage,
          is_favorite: this.isFavorite(foodId)
        });
      }
    });
    
    return foods;
  }

  // 원본 음식 데이터 찾기 (캐시된 데이터에서)
  findOriginalFoodData(foodId) {
    return this.cachedFoods.find(food => food.food_id === foodId) || null;
  }

  // 정렬 라벨 업데이트
  updateSortLabel(order) {
    const sortLabel = document.querySelector('.sort-label');
    if (sortLabel) {
      sortLabel.textContent = order || '정렬';
    }
  }

  // 정렬 옵션 활성화 상태 업데이트
  updateSortOptionStates(selectedOrder) {
    const sortOptions = document.querySelectorAll('.sort-option');
    sortOptions.forEach(option => {
      const order = option.dataset.order;
      
      if (order === selectedOrder) {
        option.classList.add('active');
      } else {
        option.classList.remove('active');
      }
      
      // 기본순인 경우 특별 처리
      if (order === '기본순' && !selectedOrder) {
        option.classList.add('active');
      }
    });
  }

  // 필터 적용
  async applyFilters() {
    this.currentFilters = this.getFilterValues();
    this.currentPage = 1;
    this.hasMoreData = true;
    this.hideFilterModal();
    
    // 더보기 버튼 숨기기
    this.hideLoadMoreButton();
    
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
    this.hasMoreData = true;
    
    // 더보기 버튼 숨기기
    this.hideLoadMoreButton();
    
    this.refineSearch();
  }

  // 세밀 검색 실행
  async refineSearch() {
    // 캐시된 데이터가 있으면 프론트엔드에서 처리
    if (this.cachedFoods.length > 0) {
      console.log('캐시된 데이터로 정렬/필터 적용:', this.cachedFoods.length);
      
      // 프론트엔드에서 정렬 및 필터링 적용
      let filteredFoods = this.applyFiltersToFoods(this.cachedFoods);
      let sortedFoods = this.sortFoods(filteredFoods, this.currentOrder);
      
      // 결과 표시
      this.mergeFavoriteStates(sortedFoods);
      this.displayFoods(sortedFoods);
      
      // 더보기 버튼 표시 여부 결정
      if (sortedFoods.length < this.ITEMS_PER_PAGE) {
        this.hasMoreData = false;
      } else {
        this.showLoadMoreButton();
      }
      
      return;
    }

    // 백엔드 API가 없으므로 프론트엔드에서 처리
    if (!this.searchToken) {
      await this.searchFoods(this.currentKeyword);
      return;
    }

    // 현재 검색 결과를 다시 표시 (정렬/필터 적용)
    this.showLoading();
    
    try {
      // 기존 검색 결과를 가져와서 프론트엔드에서 정렬/필터링
      const params = new URLSearchParams({
        keyword: this.currentKeyword,
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
      
      // 프론트엔드에서 정렬 및 필터링 적용
      if (data.foods && data.foods.length > 0) {
        let filteredFoods = this.applyFiltersToFoods(data.foods);
        let sortedFoods = this.sortFoods(filteredFoods, this.currentOrder);
        
        // 결과 표시
        this.mergeFavoriteStates(sortedFoods);
        this.displayFoods(sortedFoods);
        
        // 더보기 버튼 표시 여부 결정
        if (sortedFoods.length < this.ITEMS_PER_PAGE) {
          this.hasMoreData = false;
        } else {
          this.showLoadMoreButton();
        }
      }
      
      this.hideLoading();
    } catch (error) {
      console.error('검색 오류:', error);
      this.showToast('검색 중 오류가 발생했습니다.');
      this.hideLoading();
    }
  }

  // 프론트엔드에서 필터링 적용
  applyFiltersToFoods(foods) {
    if (Object.keys(this.currentFilters).length === 0) {
      return foods;
    }

    return foods.filter(food => {
      // 각 필터 조건 확인
      for (const [key, value] of Object.entries(this.currentFilters)) {
        const [field, type] = key.split('_');
        const foodValue = this.getFoodValue(food, field);
        
        if (type === 'min' && foodValue < value) return false;
        if (type === 'max' && foodValue > value) return false;
      }
      return true;
    });
  }

  // 음식 데이터에서 특정 영양성분 값 가져오기
  getFoodValue(food, field) {
    const fieldMap = {
      'calorie': 'calorie',
      'protein': 'protein',
      'fat': 'fat',
      'carb': 'carbohydrate',
      'salt': 'salt',
      'sugar': 'sugar'
    };
    
    const mappedField = fieldMap[field];
    return mappedField && food[mappedField] ? parseFloat(food[mappedField]) : 0;
  }

  // 프론트엔드에서 정렬 적용
  sortFoods(foods, order) {
    if (!order) return foods;

    const sortedFoods = [...foods];
    
    switch (order) {
      case '단백질이 많은':
        sortedFoods.sort((a, b) => (b.protein || 0) - (a.protein || 0));
        break;
      case '당이 적은':
        sortedFoods.sort((a, b) => (a.sugar || 0) - (b.sugar || 0));
        break;
      case '포화지방이 적은':
        sortedFoods.sort((a, b) => (a.saturated_fat || 0) - (b.saturated_fat || 0));
        break;
      case '나트륨이 적은':
        sortedFoods.sort((a, b) => (a.salt || 0) - (b.salt || 0));
        break;
      case '열량이 많은':
        sortedFoods.sort((a, b) => (b.calorie || 0) - (a.calorie || 0));
        break;
      case '열량이 적은':
        sortedFoods.sort((a, b) => (a.calorie || 0) - (b.calorie || 0));
        break;
      default:
        break;
    }
    
    return sortedFoods;
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
        this.currentFavorites[productId] = true;
      } else {
        delete this.currentFavorites[productId];
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

  // 정렬 모달 토글
  toggleSortModal() {
    const sortModal = document.getElementById('sortModal');
    const sortDropdown = document.getElementById('sortDropdown');
    
    if (sortModal) {
      const isVisible = sortModal.classList.contains('show');
      
      if (!isVisible) {
        // 모달을 열 때
        sortModal.classList.add('show');
        if (sortDropdown) {
          sortDropdown.classList.add('active');
        }
        
        // 현재 선택된 정렬 옵션 표시
        this.updateSortOptionStates(this.currentOrder);
      } else {
        // 모달을 닫을 때
        this.hideSortModal();
      }
    }
  }

  // 정렬 모달 숨기기
  hideSortModal() {
    const sortModal = document.getElementById('sortModal');
    const sortDropdown = document.getElementById('sortDropdown');
    
    if (sortModal) {
      sortModal.classList.remove('show');
    }
    
    if (sortDropdown) {
      sortDropdown.classList.remove('active');
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

  // 더보기 버튼 표시
  showLoadMoreButton() {
    const loadMoreContainer = document.getElementById('loadMoreContainer');
    if (loadMoreContainer) {
      loadMoreContainer.style.display = 'flex';
      console.log('더보기 버튼이 표시되었습니다.');
    }
  }

  // 더보기 버튼 숨김
  hideLoadMoreButton() {
    const loadMoreContainer = document.getElementById('loadMoreContainer');
    if (loadMoreContainer) {
      loadMoreContainer.style.display = 'none';
      console.log('더보기 버튼이 숨겨졌습니다.');
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
    
    // 더보기 버튼 숨기기
    this.hideLoadMoreButton();
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

// 더 많은 결과 로드하는 전역 함수
function loadMoreResults() {
  if (window.advancedResult) {
    window.advancedResult.loadMoreResults();
  }
}
