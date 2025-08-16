// 검색 입력창 클릭 시 search_before 페이지로 이동
function goToSearchBefore() {
    window.location.href = '/search/';
}

// 기존 이벤트 리스너 제거 (더 이상 필요하지 않음)
// document.getElementById('searchInput').addEventListener('click', function() {
//     const q = document.getElementById('searchInput').value.trim();
//     window.location.href = '/search/';
// });