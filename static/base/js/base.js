// ========================================
// BASE JAVASCRIPT
// ========================================

// 로그인 상태 확인 함수
function checkLoginStatus() {
    return window.isAuthenticated || false;
}

// 로그인 모달 표시
function showLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

// 로그인 모달 숨기기
function hideLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 원래 가려고 했던 페이지 URL 저장
let originalTargetUrl = '';

// 로그인 페이지로 이동 (원래 페이지 정보와 함께)
function goToLogin() {
    if (originalTargetUrl) {
        // 원래 가려고 했던 페이지 정보를 URL 파라미터로 전달
        const loginUrl = '/accounts/login/?next=' + encodeURIComponent(originalTargetUrl);
        window.location.href = loginUrl;
    } else {
        window.location.href = '/accounts/login/';
    }
}

// 회원가입 페이지로 이동
function goToSignup() {
    window.location.href = '/accounts/signup/';
}

// 로그인이 필요한 기능에 적용할 함수
function requireLogin(targetUrl) {
    if (checkLoginStatus()) {
        // 로그인된 경우 바로 이동
        window.location.href = targetUrl;
    } else {
        // 로그인되지 않은 경우 원래 URL 저장하고 모달 표시
        originalTargetUrl = targetUrl;
        showLoginModal();
    }
}

// 로그인 성공 후 원래 페이지로 이동하는 함수
function redirectAfterLogin() {
    // URL에서 next 파라미터 확인
    const urlParams = new URLSearchParams(window.location.search);
    const nextUrl = urlParams.get('next');
    
    if (nextUrl && checkLoginStatus()) {
        // 로그인된 상태이고 next 파라미터가 있으면 해당 페이지로 이동
        window.location.href = nextUrl;
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 모달 외부 클릭 시 모달 닫기
    const modal = document.getElementById('loginModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                hideLoginModal();
            }
        });
    }

    // 페이지 로드 시 로그인 후 리다이렉트 체크
    redirectAfterLogin();

    // 식사기록 버튼 클릭 시 로그인 체크
    const dietLink = document.querySelector('a[href*="/diets/"]');
    if (dietLink) {
        dietLink.addEventListener('click', function(e) {
            if (!checkLoginStatus()) {
                e.preventDefault();
                requireLogin(this.href);
            }
        });
    }

    // 분석하기 버튼 클릭 시 로그인 체크
    const analysisLink = document.querySelector('a[href*="/analysis/"]');
    if (analysisLink) {
        analysisLink.addEventListener('click', function(e) {
            if (!checkLoginStatus()) {
                e.preventDefault();
                requireLogin(this.href);
            }
        });
    }

    // 내 페이지 버튼 클릭 시 로그인 체크
    const profileLink = document.querySelector('a[href*="mypage"]');
    if (profileLink) {
        profileLink.addEventListener('click', function(e) {
            if (!checkLoginStatus()) {
                e.preventDefault();
                requireLogin(this.href);
            }
        });
    }
});
