// 롤링배너 관련 변수
let currentSlide = 0;
let totalSlides = 0;
let autoPlayInterval;

// 검색 입력창 클릭 시 search_before 페이지로 이동
function goToSearchBefore() {
    window.location.href = '/search/';
}

// 제품 상세 페이지로 이동
function goToProductDetail(foodId) {
    window.location.href = `/products/${foodId}`;
}

// 롤링배너 이동
function moveBanner(direction) {
    const banner = document.getElementById('rollingBanner');
    const indicators = document.querySelectorAll('.indicator');
    
    if (!banner) return;
    
    totalSlides = banner.children.length;
    
    if (direction === 1) {
        currentSlide = (currentSlide + 1) % totalSlides;
    } else {
        currentSlide = (currentSlide - 1 + totalSlides) % totalSlides;
    }
    
    updateBanner();
}

// 특정 슬라이드로 이동
function goToSlide(slideIndex) {
    currentSlide = slideIndex;
    updateBanner();
}

// 배너 업데이트
function updateBanner() {
    const banner = document.getElementById('rollingBanner');
    
    if (!banner) return;
    
    // 배너 위치 업데이트
    banner.style.transform = `translateX(-${currentSlide * 100}%)`;
}

// 자동 재생 시작
function startAutoPlay() {
    autoPlayInterval = setInterval(() => {
        moveBanner(1);
    }, 4000); // 4초마다 자동 이동
}

// 자동 재생 정지
function stopAutoPlay() {
    if (autoPlayInterval) {
        clearInterval(autoPlayInterval);
    }
}

// DOM 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', function() {
    const banner = document.getElementById('rollingBanner');
    if (banner) {
        totalSlides = banner.children.length;
        
        // 자동 재생 시작
        startAutoPlay();
        
        // 마우스 호버 시 자동 재생 정지
        banner.addEventListener('mouseenter', stopAutoPlay);
        banner.addEventListener('mouseleave', startAutoPlay);
    }
});

// 기존 이벤트 리스너 제거 (더 이상 필요하지 않음)
// document.getElementById('searchInput').addEventListener('click', function() {
//     const q = document.getElementById('searchInput').value.trim();
//     window.location.href = '/search/';
// });