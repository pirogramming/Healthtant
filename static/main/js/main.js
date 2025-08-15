document.getElementById('searchInput').addEventListener('click', function() {
    const q = document.getElementById('searchInput').value.trim();
    window.location.href = '/search/';
});