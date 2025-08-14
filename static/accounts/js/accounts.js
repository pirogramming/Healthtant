// ========================================
// ACCOUNTS JAVASCRIPT
// ========================================

// 비밀번호 변경 폼 검증 (password_change_form.html)
function initPasswordChangeForm() {
    const password1 = document.getElementById('password1');
    const password2 = document.getElementById('password2');
    const form = document.getElementById('password-change-form');
    const submitButton = document.querySelector('.submit-button');

    if (!password1 || !password2 || !form || !submitButton) return;

    function validatePasswords() {
        if (password1.value && password2.value) {
            if (password1.value === password2.value) {
                password2.style.borderBottomColor = '#56AAB2';
                submitButton.disabled = false;
            } else {
                password2.style.borderBottomColor = '#ff4444';
                submitButton.disabled = true;
            }
        }
    }

    password1.addEventListener('input', validatePasswords);
    password2.addEventListener('input', validatePasswords);

    // 폼 제출 시 최종 검증
    form.addEventListener('submit', function(e) {
        if (password1.value !== password2.value) {
            e.preventDefault();
            alert('비밀번호가 일치하지 않습니다.');
        }
    });
}

// 비밀번호 재설정 폼 검증 (password_reset_from_key.html)
function initPasswordResetForm() {
    // Django 템플릿에서 동적으로 생성된 ID를 사용
    const password1 = document.querySelector('input[name="password1"]');
    const password2 = document.querySelector('input[name="password2"]');
    const form = document.getElementById('password-confirm-form');
    const submitButton = document.querySelector('.submit-button');

    if (!password1 || !password2 || !form || !submitButton) return;

    function validatePasswords() {
        if (password1.value && password2.value) {
            if (password1.value === password2.value) {
                password2.style.borderBottomColor = '#56AAB2';
                submitButton.disabled = false;
            } else {
                password2.style.borderBottomColor = '#ff4444';
                submitButton.disabled = true;
            }
        }
    }

    password1.addEventListener('input', validatePasswords);
    password2.addEventListener('input', validatePasswords);

    // 폼 제출 시 최종 검증
    form.addEventListener('submit', function(e) {
        if (password1.value !== password2.value) {
            e.preventDefault();
            alert('비밀번호가 일치하지 않습니다.');
        }
    });
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 비밀번호 변경 폼이 있는 경우 초기화
    if (document.getElementById('password-change-form')) {
        initPasswordChangeForm();
    }
    
    // 비밀번호 재설정 폼이 있는 경우 초기화
    if (document.getElementById('password-confirm-form')) {
        initPasswordResetForm();
    }
}); 