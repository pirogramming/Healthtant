const getCookie = (name) => {
	const m = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]*)'));
	return m ? decodeURIComponent(m[2]) : '';
};
const getCsrfToken = () => getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', () => {
	const favoriteBtn = document.getElementById('favoriteBtn');
	if (!favoriteBtn) return;

	const isAuthenticated = favoriteBtn.dataset.isAuthenticated === 'true';

	const getCsrfToken = () => {
		const input = document.querySelector('[name=csrfmiddlewaretoken]');
		const meta = document.querySelector('meta[name="csrf-token"]');
		return (input && input.value) || (meta && meta.content) || '';
	};

	const toggleFavorite = async () => {
		const productId = favoriteBtn.getAttribute('data-product-id');
		if (!productId) return;

		favoriteBtn.disabled = true;
		try {
			const res = await fetch(`/products/${productId}/like/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': getCsrfToken(),
					'X-Requested-With': 'XMLHttpRequest'
				},
				credentials: 'same-origin'
			});
			if (!res.ok) throw new Error('네트워크 오류');

			const data = await res.json();
			const isFavorite = data.is_favorite;

			favoriteBtn.classList.toggle('active', isFavorite);
			favoriteBtn.setAttribute('data-is-favorite', String(isFavorite));
			favoriteBtn.setAttribute('aria-pressed', String(isFavorite));
		} catch (e) {
			console.error('찜 처리 오류:', e);
		} finally {
			favoriteBtn.disabled = false;
		}
	};

	favoriteBtn.addEventListener('click', (e) => {
		e.preventDefault();

		if (!isAuthenticated) {
			const modal = document.getElementById('loginModal');
			if (modal) {
				modal.style.display = 'flex';  // 가운데 정렬용
				modal.classList.add('show');
			} else {
				alert('로그인이 필요한 기능입니다.');
			}
			return;
		}

		toggleFavorite();
	});
});