// ========================================
// MYPAGE JAVASCRIPT
// ========================================

// ========================================
// MYPAGE PROFILE (mypage_profile.html)
// ========================================

// 로그아웃 모달 생성 (함수 선언문)
function createLogoutModal() {
    const modalHTML = `
        <div class="modal-overlay" id="logoutModal">
            <div class="modal-container">
                <div class="modal-content">
                    <p class="modal-message">로그아웃 하시겠습니까?</p>
                    <div class="modal-buttons">
                        <button class="modal-button cancel-button">취소</button>
                        <button class="modal-button confirm-button">확인</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // 이벤트 리스너 추가
    const cancelButton = document.querySelector('#logoutModal .cancel-button');
    const confirmButton = document.querySelector('#logoutModal .confirm-button');
    const modal = document.getElementById('logoutModal');
    
    if (cancelButton) {
        cancelButton.addEventListener('click', closeLogoutModal);
    }
    
    if (confirmButton) {
        confirmButton.addEventListener('click', performLogout);
    }
    
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeLogoutModal();
            }
        });
    }
}

// 로그아웃 확인 모달 표시
function confirmLogout() {
    const modal = document.getElementById('logoutModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

// 로그아웃 모달 닫기
function closeLogoutModal() {
    const modal = document.getElementById('logoutModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 로그아웃 실행
function performLogout() {
    // Django allauth 로그아웃 URL로 이동
    window.location.href = '/accounts/logout/';
}

// 프로필 편집 페이지로 이동
function goToProfilePage() {
    // 프로필 편집 페이지로 직접 이동
    window.location.href = '/accounts/profile/edit/';
}

// 로그인 상태 확인 함수
function checkLoginStatus() {
    return window.isAuthenticated || false;
}

// 로그인이 필요한 기능에 적용할 함수
function requireLogin(callback) {
    if (checkLoginStatus()) {
        // 로그인된 경우 원래 기능 실행
        if (callback) callback();
    } else {
        // 로그인되지 않은 경우 모달 표시
        showLoginModal();
    }
}

// ========================================
// LOGIN MODAL FUNCTIONS (base.html 공통)
// ========================================

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

// 로그인 페이지로 이동
function goToLogin() {
    window.location.href = '/accounts/login/';
}

// 회원가입 페이지로 이동
function goToSignup() {
    window.location.href = '/accounts/signup/';
}

// ========================================
// MYPAGE FAVORITE FOODS (mypage_favorite_foods.html)
// ========================================

// 검색 수행 함수
function performSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;
    
    const keyword = searchInput.value.trim();
    
    if (!keyword) {
        alert('검색어를 입력해주세요.');
        return;
    }
    
    // 실제 검색 기능 구현 시 여기에 AJAX 요청 추가
    console.log('검색어:', keyword);
}


// mypage.js
//혹시 수정하고 싶다면 여기 toggleFavorite 함수 수정하면 됨
//이름만 잘 지정하면 돌아갈거임~
function toggleFavorite(foodId, button) {
    if (button.classList.contains('active')) {
        if (confirm('즐겨찾기에서 제거하시겠습니까?')) {
            // POST 요청으로 변경
            fetch(`/mypage/food/like/${foodId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
            })
            .then(response => {
                if (response.ok) {
                    // 성공 시 즐겨찾기 목록 페이지로 이동
                    window.location.href = '/mypage/food/like/';
                } else {
                    alert('즐겨찾기 제거에 실패했습니다.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('즐겨찾기 제거 중 오류가 발생했습니다.');
            });
        }
    } 
}

// CSRF 토큰 가져오기
function getCookie(name) {
    const v = `; ${document.cookie}`;
    const p = v.split(`; ${name}=`);
    if (p.length === 2) return p.pop().split(";").shift();
}

// 뒤로가기 함수
function goBack() {
    // 마이페이지로 돌아가기
    window.location.href = '/mypage/';
}

// ========================================
// MYPAGE WITHDRAW CONFIRM (mypage_withdraw_confirm.html)
// ========================================

// 제출 버튼 토글 함수
function toggleSubmitButton() {
    const checkbox = document.getElementById('agreeCheckbox');
    const submitButton = document.getElementById('submitButton');
    
    if (!checkbox || !submitButton) return;
    
    if (checkbox.checked) {
        submitButton.disabled = false;
        submitButton.classList.add('active');
    } else {
        submitButton.disabled = true;
        submitButton.classList.remove('active');
    }
}

// ========================================
// 페이지 로드 시 초기화
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    // 로그아웃 모달 생성
    // createLogoutModal();
    
    const logoutBtn = document.querySelector('.section-title');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            createLogoutModal();
            confirmLogout();
        });
    }
    
    // ========================================
    // MYPAGE PROFILE 초기화
    // ========================================
    // 페이지 로드 시 서버 이미지 우선 표시
    const serverImageUrl = window.serverImageUrl || '';
    const profilePicture = document.querySelector('.profile-picture');
    
    if (serverImageUrl && serverImageUrl.trim() !== '' && serverImageUrl !== 'default.png' && profilePicture) {
        profilePicture.innerHTML = `<img src="${serverImageUrl}" alt="프로필 이미지" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`;
    }

    // 마이페이지 접근 시 로그인 체크
    if (!checkLoginStatus()) {
        showLoginModal();
    }

    // ========================================
    // LOGIN MODAL 초기화 (base.html 공통)
    // ========================================
    const loginModal = document.getElementById('loginModal');
    if (loginModal) {
        // 모달 외부 클릭 시 로그인 페이지로 이동
        loginModal.addEventListener('click', function(e) {
            if (e.target === this) {
                window.location.href = '/accounts/login/';
            }
        });
    }

    // ========================================
    // MYPAGE FAVORITE FOODS 초기화
    // ========================================
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        // Enter 키로도 검색 가능하도록
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }

    // ========================================
    // MYPAGE WITHDRAW CONFIRM 초기화
    // ========================================
    const withdrawForm = document.getElementById('withdrawForm');
    if (withdrawForm) {
        // 폼 제출 시 재확인
        withdrawForm.addEventListener('submit', function(e) {
            const agreeCheckbox = document.getElementById('agreeCheckbox');
            if (!agreeCheckbox || !agreeCheckbox.checked) {
                e.preventDefault();
                alert('동의 사항을 체크해주세요.');
                return false;
            }
            
            if (!confirm('정말로 탈퇴하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
                e.preventDefault();
                return false;
            }
        });
    }
});
