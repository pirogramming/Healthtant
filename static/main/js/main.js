// ========================================
// MAIN JAVASCRIPT
// ========================================

// ========================================
// CSV UPLOAD (csv_upload.html)
// ========================================

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    // CSV 업로드 페이지인 경우에만 실행
    if (document.getElementById('uploadForm')) {
        loadStats();
        setupFileInput();
    }
});

// 파일 입력 설정
function setupFileInput() {
    const fileInput = document.getElementById('csvFile');
    const fileInfo = document.getElementById('fileInfo');

    if (!fileInput || !fileInfo) return;

    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const size = (file.size / 1024 / 1024).toFixed(2);
            fileInfo.innerHTML = `선택된 파일: ${file.name} (${size} MB)`;
        } else {
            fileInfo.innerHTML = '';
        }
    });
}

// 통계 로드
async function loadStats() {
    try {
        const response = await fetch('/db-stats/');
        const data = await response.json();

        if (data.success) {
            const stats = data.data;
            const foodCountEl = document.getElementById('foodCount');
            const priceCountEl = document.getElementById('priceCount');
            const avgPriceEl = document.getElementById('avgPrice');
            const categoryCountEl = document.getElementById('categoryCount');

            if (foodCountEl) foodCountEl.textContent = stats.food.total_count;
            if (priceCountEl) priceCountEl.textContent = stats.price.total_count;
            if (avgPriceEl) avgPriceEl.textContent = Math.round(stats.price.avg_price).toLocaleString() + '원';
            if (categoryCountEl) categoryCountEl.textContent = stats.food.categories.length;
        }
    } catch (error) {
        console.error('통계 로드 실패:', error);
    }
}

// 파일 업로드
function setupUploadForm() {
    const uploadForm = document.getElementById('uploadForm');
    if (!uploadForm) return;

    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const formData = new FormData();
        const fileInput = document.getElementById('csvFile');
        const tableType = document.getElementById('tableType');
        const uploadMode = document.getElementById('uploadMode');

        if (!fileInput || !tableType || !uploadMode) return;

        if (!fileInput.files[0]) {
            showResult('파일을 선택해주세요.', 'error');
            return;
        }

        formData.append('csv_file', fileInput.files[0]);
        formData.append('table_type', tableType.value);
        formData.append('upload_mode', uploadMode.value);

        // UI 상태 변경
        const uploadBtn = document.getElementById('uploadBtn');
        const loading = document.getElementById('loading');

        if (uploadBtn) uploadBtn.disabled = true;
        if (loading) loading.style.display = 'block';
        hideResult();

        try {
            const response = await fetch('/upload-csv/', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                showResult(`
                    <h3>업로드 성공!</h3>
                    <p>${result.message}</p>
                    <div>
                        <p><strong>파일 정보:</strong></p>
                        <ul>
                            <li>파일명: ${result.data.file_info.filename}</li>
                            <li>총 행 수: ${result.data.file_info.total_rows}</li>
                            <li>처리된 행: ${result.data.file_info.processed_rows}</li>
                            <li>삽입된 행: ${result.data.file_info.inserted_rows}</li>
                            <li>업데이트된 행: ${result.data.file_info.updated_rows}</li>
                            <li>건너뛴 행: ${result.data.file_info.skipped_rows}</li>
                            <li>오류 행: ${result.data.file_info.error_rows}</li>
                        </ul>
                    </div>
                    <div>
                        <h4>처리 상세:</h4>
                        ${result.data.processing_details.map(detail => 
                            `<div>${detail}</div>`
                        ).join('')}
                    </div>
                `, 'success');

                // 통계 새로고침
                setTimeout(loadStats, 1000);
            } else {
                showResult(`업로드 실패: ${result.message}`, 'error');
            }
        } catch (error) {
            showResult(`네트워크 오류: ${error.message}`, 'error');
        } finally {
            if (uploadBtn) uploadBtn.disabled = false;
            if (loading) loading.style.display = 'none';
        }
    });
}

// 결과 표시
function showResult(message, type) {
    const result = document.getElementById('result');
    if (!result) return;

    result.innerHTML = message;
    result.style.display = 'block';
    result.style.padding = '10px';
    result.style.margin = '10px 0';
    
    if (type === 'success') {
        result.style.backgroundColor = '#d4edda';
        result.style.border = '1px solid #c3e6cb';
        result.style.color = '#155724';
    } else {
        result.style.backgroundColor = '#f8d7da';
        result.style.border = '1px solid #f5c6cb';
        result.style.color = '#721c24';
    }
}

function hideResult() {
    const result = document.getElementById('result');
    if (result) {
        result.style.display = 'none';
    }
}

// 템플릿 다운로드
async function downloadTemplate(tableType) {
    try {
        const response = await fetch(`/csv-template/?table_type=${tableType}`);
        const data = await response.json();

        if (data.success) {
            const template = data.data;
            const csvContent = [template.columns.join(','), template.sample_data.join(',')].join('\n');
            
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            
            link.setAttribute('href', url);
            link.setAttribute('download', `${tableType}_template.csv`);
            link.style.visibility = 'hidden';
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } else {
            alert('템플릿 다운로드 실패: ' + data.message);
        }
    } catch (error) {
        alert('템플릿 다운로드 중 오류가 발생했습니다: ' + error.message);
    }
}

// ========================================
// MAIN MAINPAGE (main_mainpage.html)
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
    
    // 검색 페이지로 이동
    window.location.href = `/products/search/?keyword=${encodeURIComponent(keyword)}`;
}
