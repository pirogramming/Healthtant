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

// 영양 정보 불러오기
document.addEventListener('DOMContentLoaded', async () => {
	const container = document.querySelector('.health-info');
	const btn = document.getElementById('favoriteBtn');
	if (!container || !btn) return;
  
	const pid = btn.getAttribute('data-product-id');
	try {
	  const res = await fetch(`/products/${pid}/?format=json`, { credentials: 'same-origin' });
	  if (!res.ok) return;
	  const p = await res.json();
  
	  const good = [];
	  const bad = [];
	  const neutral = [];
  
	  const pushByClass = (obj, name) => {
		if (!obj || !obj.class) return;
		const text = `이 제품은 <span class="highlight">${name}이 ${obj.level}</span> 제품입니다.`;
		if (obj.class === 'GOOD') good.push(text);
		if (obj.class === 'BAD') bad.push(text);
		if (obj.class === 'NEUTRAL') neutral.push(text);
	  };
	  
	  //여기는 열량은 일부러 넣지 않은거니까 추가할 필요없음!
	  pushByClass(p.sugar_level, '당류');
	  pushByClass(p.saturated_fatty_acids_level, '포화지방');
	  pushByClass(p.salt_level, '나트륨');
	  pushByClass(p.protein_level, '단백질');
	  
	let html = '';
	if (good.length) {
	html += `
	<div class="health-group good">
		<div class="health-item">
		<div class="left">
			<span class="health-badge">GOOD</span>
		</div>
		<div class="right">
			<span class="health-text">${good[0]}</span>
		</div>
		</div>
		${good.slice(1).map(t => `
		<div class="health-item indent">
			<div class="left"></div>
			<div class="right">
			<span class="health-text">${t}</span>
			</div>
		</div>
		`).join('')}
	</div>`;
	}
	if (bad.length) {
	html += `
	<div class="health-group bad">
		<div class="health-item">
		<div class="left">
			<span class="health-badge">BAD</span>
		</div>
		<div class="right">
			<span class="health-text">${bad[0]}</span>
		</div>
		</div>
		${bad.slice(1).map(t => `
		<div class="health-item indent">
			<div class="left"></div>
			<div class="right">
			<span class="health-text">${t}</span>
			</div>
		</div>
		`).join('')}
	</div>`;
	}
	if (neutral.length) {
		html += `
		<div class="health-group neutral">
		  <div class="health-item">
			<div class="left">
			  <span class="health-badge">NEUTRAL</span>
			</div>
			<div class="right">
			  <span class="health-text">${neutral[0]}</span>
			</div>
		  </div>
		  ${neutral.slice(1).map(t => `
			<div class="health-item indent">
			  <div class="left"></div>
			  <div class="right">
				<span class="health-text">${t}</span>
			  </div>
			</div>
		  `).join('')}
		</div>`;
	}
	  container.innerHTML = html || '<div class="health-item"><span class="health-text">이 제품의 영양 정보를 분석 중입니다.</span></div>';
	} catch (e) {
	  console.error(e);
	}
  });

  document.addEventListener('DOMContentLoaded', async () => {
	const container = document.querySelector('.nutrition-table');
	const btn = document.getElementById('favoriteBtn');
	if (!container || !btn) return;
  
	const pid = btn.getAttribute('data-product-id');
	try {
	  const res = await fetch(`/products/${pid}/?format=json`, { credentials: 'same-origin' });
	  if (!res.ok) return;
	  const p = await res.json();
  
	  // 영양소 데이터 정의
	  const nutritionData = [
		['열량', p.calorie, 'kcal'],
		['수분', p.moisture, 'g'],
		['단백질', p.protein, 'g'],
		['지방', p.fat, 'g'],
		['탄수화물', p.carbohydrate, 'g'],
		['당류', p.sugar, 'g'],
		['식이섬유', p.dietary_fiber, 'g'],
		['칼슘', p.calcium, 'mg'],
		['철분', p.iron_content, 'mg'],
		['인', p.phosphorus, 'mg'],
		['칼륨', p.potassium, 'mg'],
		['나트륨', p.sodium, 'mg'],
		['비타민A', p.VitaminA, 'μg'],
		['비타민B', p.VitaminB, 'mg'],
		['비타민C', p.VitaminC, 'mg'],
		['비타민D', p.VitaminD, 'μg'],
		['비타민E', p.VitaminE, 'mg'],
		['콜레스테롤', p.cholesterol, 'mg'],
		['포화지방산', p.saturated_fatty_acids, 'g'],
		['트랜스지방산', p.trans_fatty_acids, 'g'],
		['마그네슘', p.magnesium, 'mg'],
	  ];
  
	  let html = '';
	  nutritionData.forEach(([name, value, unit], index) => {
		if (value !== null && value !== undefined) {
		  html += `
			<div class="nutrition-row${index > 0 ? ' divider' : ''}">
			  <span class="nutrition-name">${name}</span>
			  <span class="nutrition-amount">${Math.round(value)}${unit}</span>
			</div>
		  `;
		}
	  });
  
	  container.innerHTML = html || '<div class="nutrition-row"><span class="nutrition-text">영양 정보를 불러오는 중...</span></div>';
	} catch (e) {
	  console.error(e);
	}
  });

// letter_grade를 가져와서 brand-tag 업데이트
document.addEventListener('DOMContentLoaded', async () => {
	const brandTag = document.querySelector('.brand-tag');
	const btn = document.getElementById('favoriteBtn');
	if (!brandTag || !btn) return;
  
	const pid = btn.getAttribute('data-product-id');
	try {
	  const res = await fetch(`/products/${pid}/?format=json`, { credentials: 'same-origin' });
	  if (!res.ok) return;
	  const p = await res.json();
  
	  // letter_grade가 있으면 brand-tag 업데이트
	  if (p.letter_grade) {
		brandTag.textContent = p.letter_grade;
		
		// 등급에 따른 색상 클래스 추가 (선택사항)
		// brandTag.className = 'brand-tag';
		// brandTag.classList.add(`grade-${p.letter_grade.toLowerCase()}`);
	  }
	} catch (e) {
	  console.error('등급 정보를 불러오는 중 오류:', e);
	}
  });