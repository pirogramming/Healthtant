function performSearch() {
    const searchInput = document.getElementById('searchInput');
    const keyword = searchInput.value.trim();
    
    if (!keyword) {
        alert('검색어를 입력해주세요.');
        return;
    }
    
    // AJAX 요청
    fetch(`/search/normal/?keyword=${encodeURIComponent(keyword)}`)
        .then(response => response.json())
        .then(data => {
            displaySearchResults(data.foods);
        })
        .catch(error => {
            console.error('검색 중 오류가 발생했습니다:', error);
            alert('검색 중 오류가 발생했습니다.');
        });
}

function displaySearchResults(foods) {
    const searchResults = document.getElementById('searchResults');
    const searchResultsList = document.getElementById('searchResultsList');
    
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
});