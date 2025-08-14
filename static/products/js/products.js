const getCookie = (name) => {
	const m = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]*)'));
	return m ? decodeURIComponent(m[2]) : '';
};
const getCsrfToken = () => getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', () => {
	const favoriteBtn = document.getElementById('favoriteBtn');
	if (!favoriteBtn) return;

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
			if (data.is_favorite) {
				favoriteBtn.classList.add('active');
				favoriteBtn.setAttribute('data-is-favorite', 'true');
				favoriteBtn.setAttribute('aria-pressed', 'true');
			} else {
				favoriteBtn.classList.remove('active');
				favoriteBtn.setAttribute('data-is-favorite', 'false');
				favoriteBtn.setAttribute('aria-pressed', 'false');
			}
		} catch (e) {
			console.error('좋아요 처리 오류:', e);
		} finally {
			favoriteBtn.disabled = false;
		}
	};

	favoriteBtn.addEventListener('click', (e) => {
		e.preventDefault();
		toggleFavorite();
	});
});