// ========================================
// ANALYSIS JAVASCRIPT
// ========================================

// 분석 날짜 선택 페이지 (analysis_date.html)
function initAnalysisDate() {
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    if (!startDateInput || !endDateInput || !analyzeBtn) return;
    
    // 오늘 날짜 설정
    const today = new Date().toISOString().split('T')[0];
    
    // 기본값을 오늘로 설정
    endDateInput.value = today;
    
    // 일주일 전을 시작일로 설정
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    startDateInput.value = weekAgo.toISOString().split('T')[0];
    
    // 날짜 유효성 검사
    function validateDates() {
        const startDate = new Date(startDateInput.value);
        const endDate = new Date(endDateInput.value);
        
        if (startDate && endDate) {
            if (startDate > endDate) {
                analyzeBtn.disabled = true;
                analyzeBtn.textContent = '시작일이 종료일보다 늦습니다';
                return false;
            } else if (endDate > new Date(today)) {
                analyzeBtn.disabled = true;
                analyzeBtn.textContent = '미래 날짜는 선택할 수 없습니다';
                return false;
            } else {
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = '분석하기';
                return true;
            }
        }
        return false;
    }
    
    // 시작일 변경 시 종료일 최소값 설정
    startDateInput.addEventListener('change', function() {
        endDateInput.min = this.value;
        validateDates();
    });
    
    // 종료일 변경 시 시작일 최대값 설정
    endDateInput.addEventListener('change', function() {
        startDateInput.max = this.value;
        validateDates();
    });
    
    // 초기 유효성 검사
    validateDates();
    
    // 폼 제출 시 추가 검증
    const form = document.querySelector('.date-selection-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!validateDates()) {
                e.preventDefault();
                alert('올바른 날짜를 선택해주세요.');
            }
        });
    }

    // 로그인 상태 확인 함수
    function checkLoginStatus() {
        return window.isAuthenticated || false;
    }

    // 분석하기 버튼 클릭 시 로그인 체크
    analyzeBtn.addEventListener('click', function(e) {
        if (!checkLoginStatus()) {
            e.preventDefault();
            showLoginModal();
        }
    });
}

// 분석 메인 페이지 차트 (analysis_main.html)
function initAnalysisMain() {
    const el = document.getElementById('category-data');
    const target = document.getElementById('categoryChart');
    if (!el || !target) return;

    let data = [];
    try { 
        data = JSON.parse(el.textContent || '[]'); 
    } catch (_) {}

    if (!Array.isArray(data) || data.length === 0) {
        // 차트 컨테이너의 부모 요소에 메시지 추가
        const chartSurface = target.parentElement;
        
        // 기존 메시지가 있다면 제거
        const existingMessage = chartSurface.querySelector('.no-data-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        // 메시지를 차트 위에 추가
        const message = document.createElement('div');
        message.className = 'no-data-message';
        message.textContent = '데이터가 부족합니다.';
        chartSurface.insertBefore(message, target);
        
        // 빈 막대 차트 생성 (라벨 없음)
        const emptyCategories = ['', '', '', '', ''];
        const frag = document.createDocumentFragment();
        
        emptyCategories.forEach((category) => {
            const wrap = document.createElement('div');
            wrap.className = 'bar-item';

            const track = document.createElement('div');
            track.className = 'bar-track empty-bar';

            const fill = document.createElement('div');
            fill.className = 'bar-fill empty-fill';
            fill.style.height = '0%';

            track.appendChild(fill);

            const label = document.createElement('div');
            label.className = 'bar-label';
            label.textContent = category; 

            wrap.appendChild(track);
            wrap.appendChild(label);
            frag.appendChild(wrap);
        });

        target.innerHTML = '';
        target.appendChild(frag);
        return;
    }

    // 상위 6개만 사용 (이미 정렬돼 있다면 그대로, 아니라면 정렬)
    data = data.sort((a,b) => (b.count||0) - (a.count||0)).slice(0, 6);
    const max = Math.max(...data.map(d => d.count || 0), 1);

    const frag = document.createDocumentFragment();
    data.forEach(({ food_category, count }) => {
        const wrap = document.createElement('div');
        wrap.className = 'bar-item';

        const track = document.createElement('div');
        track.className = 'bar-track';

        const fill = document.createElement('div');
        fill.className = 'bar-fill';
        const h = Math.round((count / max) * 100);
        fill.style.height = Math.max(8, h) + '%'; // 최소 8% 보장

        track.appendChild(fill);

        // 툴팁
        const tooltip = document.createElement('div');
        tooltip.className = 'bar-tooltip';
        tooltip.textContent = `${count}개`;
        track.appendChild(tooltip); // track 안에 추가

        const label = document.createElement('div');
        label.className = 'bar-label';
        label.textContent = food_category || '기타';

        wrap.appendChild(track);
        wrap.appendChild(label);
        frag.appendChild(wrap);
    });

    target.innerHTML = '';
    target.appendChild(frag);
}

// 분석 다이어트 페이지 차트 (analysis_diet.html)
function initAnalysisDiet() {
    const ctx = document.getElementById('calorieChart');
    if (!ctx) return;
    
    const context = ctx.getContext('2d');
    
    // 그라디언트 생성
    const gradient = context.createLinearGradient(0, 0, 0, 280);
    gradient.addColorStop(0, '#56AAB2');
    gradient.addColorStop(1, 'rgba(217, 217, 217, 0)');
    
    // Django 템플릿에서 데이터 가져오기
    const chartData = {
        labels: window.calorieChartLabels || [],
        datasets: [{
            label: '칼로리 섭취량',
            data: window.calorieChartData || [],
            borderColor: '#56AAB2',
            backgroundColor: gradient,
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: function(context) {
                const value = context.parsed.y;
                const minValue = window.calorieChartMin || 0;
                const maxValue = window.calorieChartMax || 0;
                
                if (value === minValue) return '#56AAB2';
                if (value === maxValue) return '#EF4444';
                return '#56AAB2';
            },
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2,
            pointRadius: 6,
            pointHoverRadius: 8
        }]
    };

    const config = {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#7CC7C2',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return context.parsed.y + ' kcal';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: '#f0f0f0',
                        drawBorder: false
                    },
                    ticks: {
                        font: {
                            size: 12
                        },
                        color: '#666'
                    }
                },
                y: {
                    grid: {
                        color: '#f0f0f0',
                        drawBorder: false
                    },
                    ticks: {
                        font: {
                            size: 12
                        },
                        color: '#666',
                        callback: function(value) {
                            return value + ' kcal';
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    };

    new Chart(context, config);
}

// 분석 영양소 페이지 (analysis_nutrients.html)
function initAnalysisNutrients() {
    console.log('Nutrients analysis page loaded');
}

// 로그인 모달 관련 함수들
function showLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function hideLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function goToLogin() {
    window.location.href = '/accounts/login/';
}

function goToSignup() {
    window.location.href = '/accounts/signup/';
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 분석 날짜 선택 페이지 초기화
    if (document.getElementById('start_date') && document.getElementById('end_date')) {
        initAnalysisDate();
    }
    
    // 분석 메인 페이지 초기화
    if (document.getElementById('categoryChart')) {
        initAnalysisMain();
    }
    
    // 분석 다이어트 페이지 초기화
    if (document.getElementById('calorieChart')) {
        initAnalysisDiet();
    }
    
    // 분석 영양소 페이지 초기화
    if (document.querySelector('.nutrient-category')) {
        initAnalysisNutrients();
    }
    
    // 로그인 모달 외부 클릭 이벤트
    const modal = document.getElementById('loginModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                window.location.href = '/accounts/login/';
            }
        });
    }
});
