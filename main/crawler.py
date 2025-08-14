import time
import random
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from retry import retry
from django.utils import timezone
from foods.models import Food, Price


class CoupangCrawler:
    """쿠팡 제품 크롤링 클래스 (BeautifulSoup + Selenium 하이브리드)"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.ua = UserAgent()
        self.session = requests.Session()
        self.setup_driver()
        self.setup_session()
    
    def setup_session(self):
        """HTTP 세션 설정 (실제 크롤링 사례 기반 강화)"""
        try:
            # 실제 브라우저와 동일한 User-Agent 설정
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            self.session.headers.update({
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'DNT': '1',
                'Referer': 'https://www.coupang.com/',
                'Origin': 'https://www.coupang.com',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            })
            
            # 실제 쿠팡 접속 시뮬레이션을 위한 쿠키 설정
            self.session.cookies.update({
                'PCID': 'test_pcid_12345',
                'x-coupang-accept-language': 'ko_KR',
                'coupang_region': 'KR',
                'coupang_language': 'ko'
            })
            
            print(f"[CRAWLER] 실제 크롤링 사례 기반 HTTP 세션 설정 완료")
        except Exception as e:
            print(f"[CRAWLER] HTTP 세션 설정 실패: {str(e)}")
    
    def setup_driver(self):
        """Chrome 드라이버 설정 (백업용)"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')
            
            # 크롤링 감지 방지
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # User-Agent 설정
            user_agent = self.ua.random
            chrome_options.add_argument(f'--user-agent={user_agent}')
            
            # 창 크기 설정
            chrome_options.add_argument('--window-size=1920,1080')
            
            # 드라이버 생성
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 자동화 감지 방지
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print(f"[CRAWLER] Chrome 드라이버 설정 완료 (User-Agent: {user_agent})")
            
        except Exception as e:
            print(f"[CRAWLER] 드라이버 설정 실패: {str(e)}")
            self.driver = None
    
    @retry(tries=3, delay=2, backoff=2)
    def search_product(self, product_name: str, company_name: str = None) -> Optional[Dict]:
        """쿠팡에서 제품 검색 및 정보 추출 (실제 크롤링 사례 기반 강화)"""
        try:
            # 실제 크롤링 사례에서 사용하는 검색 전략
            search_queries = []
            
            # 1순위: 정확한 매칭 (가장 높은 성공률)
            if company_name:
                search_queries.append(f"{product_name} {company_name}")
                search_queries.append(f"{company_name} {product_name}")
            
            # 2순위: 제품명만 (전체)
            search_queries.append(product_name)
            
            # 3순위: 핵심 키워드 조합 (실제 크롤링에서 자주 사용)
            if len(product_name) > 3:
                words = product_name.split()
                if len(words) > 1:
                    # 가장 중요한 키워드들만 (실제 크롤링 사례 기반)
                    if len(words) >= 2:
                        search_queries.append(words[0])  # 첫 번째 단어
                        search_queries.append(words[-1])  # 마지막 단어
                        if len(words) >= 3:
                            search_queries.append(words[1])  # 중간 단어
                    
                    # 연속된 2개 단어 조합 (실제 크롤링에서 효과적)
                    for i in range(len(words) - 1):
                        combo = f"{words[i]} {words[i+1]}"
                        if len(combo) > 3:
                            search_queries.append(combo)
            
            # 4순위: 특수문자 제거 (실제 크롤링에서 필요)
            clean_name = ''.join(c for c in product_name if c.isalnum() or c.isspace())
            if clean_name != product_name and len(clean_name) > 2:
                search_queries.append(clean_name)
            
            # 5순위: 회사명만 (제품명이 너무 구체적일 때)
            if company_name and len(company_name) > 2:
                search_queries.append(company_name)
            
            # 중복 제거 및 순서 유지
            seen = set()
            unique_queries = []
            for query in search_queries:
                if query not in seen and len(query) > 1:
                    seen.add(query)
                    unique_queries.append(query)
            
            print(f"[CRAWLER] 실제 크롤링 사례 기반 검색 전략: {unique_queries}")
            
            # BeautifulSoup으로 먼저 시도 (실제 크롤링에서 더 빠름)
            for search_query in unique_queries:
                try:
                    result = self._try_search_beautifulsoup(search_query)
                    if result:
                        print(f"[CRAWLER] BeautifulSoup 검색 성공: '{search_query}'")
                        return result
                except Exception as search_error:
                    print(f"[CRAWLER] BeautifulSoup 검색 실패: '{search_query}' - {search_error}")
                    continue
            
            # BeautifulSoup 실패 시 Selenium으로 백업 시도
            if self.driver:
                print(f"[CRAWLER] BeautifulSoup 실패, Selenium 백업 시도")
                for search_query in unique_queries:
                    try:
                        result = self._try_search_selenium(search_query)
                        if result:
                            print(f"[CRAWLER] Selenium 백업 검색 성공: '{search_query}'")
                            return result
                    except Exception as search_error:
                        print(f"[CRAWLER] Selenium 백업 검색 실패: '{search_query}' - {search_error}")
                        continue
            
            print(f"[CRAWLER] 모든 검색 방법으로 실패: {product_name}")
            return None
            
        except Exception as e:
            print(f"[CRAWLER] 제품 검색 실패: {str(e)}")
            raise
    
    def retry_search_product(self, product_name: str, company_name: str = None, previous_attempts: list = None) -> Optional[Dict]:
        """제품 재검색 (실제 크롤링 사례 기반)"""
        try:
            # 이전에 시도한 검색어들
            tried_queries = set(previous_attempts or [])
            
            # 실제 크롤링 사례에서 사용하는 재검색 전략
            search_queries = []
            
            # 1순위: 제품명의 각 단어별 개별 검색 (실제 크롤링에서 효과적)
            if len(product_name) > 3:
                words = product_name.split()
                for word in words:
                    if len(word) > 2 and word not in tried_queries:
                        search_queries.append(word)
            
            # 2순위: 연속된 2개 단어 조합 (실제 크롤링에서 자주 사용)
            if len(product_name) > 5:
                words = product_name.split()
                for i in range(len(words) - 1):
                    combo = f"{words[i]} {words[i+1]}"
                    if len(combo) > 3 and combo not in tried_queries:
                        search_queries.append(combo)
            
            # 3순위: 제품명에서 숫자나 특수문자 제거 (실제 크롤링에서 필요)
            clean_name = ''.join(c for c in product_name if c.isalpha() or c.isspace())
            if clean_name != product_name and len(clean_name) > 3 and clean_name not in tried_queries:
                search_queries.append(clean_name)
            
            # 4순위: 회사명 기반 검색 (실제 크롤링에서 효과적)
            if company_name and len(company_name) > 2:
                # 회사명 + 제품 카테고리 추정 (실제 크롤링에서 사용)
                if any(keyword in product_name.lower() for keyword in ['밥', '김치', '라면', '과자', '음료', '우유', '빵', '치킨', '피자', '햄버거']):
                    category = '식품'
                    search_queries.append(f"{company_name} {category}")
                    search_queries.append(f"{category} {company_name}")
                
                # 회사명만으로 검색
                if company_name not in tried_queries:
                    search_queries.append(company_name)
            
            # 5순위: 제품명의 동의어나 유사어 (실제 크롤링에서 사용)
            synonyms = self._get_product_synonyms(product_name)
            for synonym in synonyms:
                if synonym not in tried_queries and len(synonym) > 2:
                    search_queries.append(synonym)
            
            # 중복 제거 및 이전 시도 제외
            final_queries = []
            for query in search_queries:
                if query not in tried_queries and query not in final_queries:
                    final_queries.append(query)
            
            print(f"[CRAWLER] 실제 크롤링 사례 기반 재검색 전략: {final_queries}")
            
            if not final_queries:
                print(f"[CRAWLER] 재검색할 새로운 검색어가 없음")
                return None
            
            # BeautifulSoup으로 재검색 (실제 크롤링에서 더 빠름)
            for search_query in final_queries:
                try:
                    result = self._try_search_beautifulsoup(search_query)
                    if result:
                        print(f"[CRAWLER] 재검색 성공: '{search_query}'")
                        return result
                except Exception as search_error:
                    print(f"[CRAWLER] 재검색 실패: '{search_query}' - {search_error}")
                    continue
            
            # Selenium으로 재검색 (백업)
            if self.driver:
                for search_query in final_queries:
                    try:
                        result = self._try_search_selenium(search_query)
                        if result:
                            print(f"[CRAWLER] Selenium 재검색 성공: '{search_query}'")
                            return result
                    except Exception as search_error:
                        print(f"[CRAWLER] Selenium 재검색 실패: '{search_query}' - {search_error}")
                        continue
            
            print(f"[CRAWLER] 모든 재검색 방법으로 실패: {product_name}")
            return None
            
        except Exception as e:
            print(f"[CRAWLER] 재검색 실패: {str(e)}")
            return None
    
    def _get_product_synonyms(self, product_name: str) -> list:
        """제품명의 동의어나 유사어 반환 (실제 크롤링 사례 기반)"""
        synonyms = []
        
        # 실제 크롤링에서 자주 사용되는 식품 동의어
        food_synonyms = {
            '밥': ['쌀', '현미', '잡곡', '곡물', '백미', '흑미'],
            '김치': ['김치', '절임', '발효', '배추김치', '총각김치'],
            '라면': ['면', '국수', '즉석면', '컵라면', '생라면'],
            '과자': ['스낵', '쿠키', '비스킷', '크래커', '초코파이'],
            '음료': ['드링크', '주스', '탄산음료', '커피', '차'],
            '우유': ['우유', '유제품', '생우유', '저지방우유', '고칼슘우유'],
            '빵': ['빵', '베이커리', '제과', '식빵', '크로아상'],
            '치킨': ['닭고기', '프라이드치킨', '치킨', '양념치킨', '후라이드'],
            '피자': ['피자', '이탈리안', '도우', '치즈피자', '페퍼로니'],
            '햄버거': ['버거', '샌드위치', '패티', '치즈버거', '불고기버거'],
            '김': ['김', '해조류', '바다김', '구운김', '조미김'],
            '소시지': ['소시지', '햄', '육가공품', '프랑크푸르트'],
            '아이스크림': ['아이스크림', '젤라토', '빙수', '아이스바'],
            '초콜릿': ['초콜릿', '초코', '다크초코', '밀크초코'],
            '사과': ['사과', '과일', '애플', '홍로', '양광']
        }
        
        # 제품명에서 키워드 찾기
        for keyword, synonym_list in food_synonyms.items():
            if keyword in product_name.lower():
                synonyms.extend(synonym_list)
                break
        
        # 제품명의 일부를 동의어로 추가 (실제 크롤링에서 효과적)
        if len(product_name) > 5:
            words = product_name.split()
            if len(words) >= 2:
                # 첫 번째와 마지막 단어의 조합
                synonyms.append(f"{words[0]} {words[-1]}")
                # 중간 단어들
                if len(words) >= 3:
                    synonyms.append(f"{words[1]} {words[2]}")
                    # 첫 번째와 중간 단어
                    synonyms.append(f"{words[0]} {words[1]}")
        
        return list(set(synonyms))  # 중복 제거
    
    def _try_search_beautifulsoup(self, search_query: str) -> Optional[Dict]:
        """BeautifulSoup을 사용한 제품 검색 (강화된 버전)"""
        try:
            # 쿠팡 검색 페이지 접속
            search_url = f"https://www.coupang.com/np/search?q={search_query}"
            print(f"[CRAWLER] BeautifulSoup 검색 시도: {search_query}")
            print(f"[CRAWLER] 검색 URL: {search_url}")
            
            # HTTP 요청 (더 긴 타임아웃과 재시도)
            response = None
            for attempt in range(3):
                try:
                    response = self.session.get(search_url, timeout=15)
                    response.raise_for_status()
                    break
                except Exception as e:
                    print(f"[CRAWLER] 요청 시도 {attempt + 1} 실패: {e}")
                    if attempt < 2:
                        time.sleep(2)
                    else:
                        raise
            
            if not response:
                return None
            
            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 페이지 제목 확인
            page_title = soup.title.string if soup.title else "제목 없음"
            print(f"[CRAWLER] 페이지 제목: {page_title}")
            
            # 페이지 크기 확인
            print(f"[CRAWLER] 페이지 크기: {len(response.text)} 문자")
            
            # 검색 결과 확인 (더 많은 패턴)
            no_result_patterns = [
                "검색 결과가 없습니다", "상품이 없습니다", "검색결과가 없습니다",
                "no results", "no products", "empty results"
            ]
            
            if any(pattern in response.text for pattern in no_result_patterns):
                print(f"[CRAWLER] 검색 결과 없음: {search_query}")
                return None
            
            # 제품 요소 찾기 (최신 쿠팡 CSS 선택자)
            product_element = self._find_product_element_beautifulsoup(soup)
            
            if product_element:
                # 제품 정보 추출
                product_info = self.extract_product_info_beautifulsoup(product_element)
                if product_info:
                    print(f"[CRAWLER] 제품 정보 추출 성공: {product_info['name']}")
                    return product_info
            
            # 제품을 찾지 못한 경우 페이지 디버깅
            print(f"[CRAWLER] 페이지 디버깅 정보:")
            print(f"[CRAWLER] - 모든 div 개수: {len(soup.find_all('div'))}")
            print(f"[CRAWLER] - 모든 li 개수: {len(soup.find_all('li'))}")
            print(f"[CRAWLER] - 가격 관련 텍스트 포함 여부: {'원' in response.text or '₩' in response.text}")
            
            return None
            
        except Exception as e:
            print(f"[CRAWLER] BeautifulSoup 검색 시도 실패: {search_query} - {str(e)}")
            return None
    
    def _find_product_element_beautifulsoup(self, soup: BeautifulSoup):
        """BeautifulSoup으로 제품 요소 찾기 (실제 크롤링 사례 기반)"""
        try:
            # 실제 쿠팡 크롤링 사례에서 사용하는 CSS 선택자들
            selectors = [
                # 1순위: 실제 작동하는 선택자들 (웹 검색 결과 기반)
                'li.search-product',
                'div.search-product',
                'div[data-product-id]',
                'div.search-product-wrap',
                'li[data-product-id]',
                
                # 2순위: 일반적인 제품 컨테이너
                'div.product-item',
                'div.product-card',
                'div.new-product-container',
                'div.product-container',
                'div.item-container',
                'div.card-container',
                
                # 3순위: 클래스명에 제품 관련 키워드가 포함된 요소들
                'div[class*="product"]',
                'li[class*="product"]',
                'div[class*="item"]',
                'div[class*="card"]',
                'div[class*="search"]',
                'li[class*="search"]',
                
                # 4순위: 더 일반적인 선택자들
                'div[class*="goods"]',
                'div[class*="item"]',
                'div[class*="list"]'
            ]
            
            for selector in selectors:
                try:
                    elements = soup.select(selector)
                    if elements:
                        print(f"[CRAWLER] BeautifulSoup으로 제품 요소 {len(elements)}개 찾음: {selector}")
                        # 첫 번째 제품 반환 (가장 관련성 높은 것)
                        return elements[0]
                except Exception as selector_error:
                    print(f"[CRAWLER] 선택자 오류 {selector}: {selector_error}")
                    continue
            
            # 마지막 시도: 페이지 소스에서 제품 관련 키워드 확인
            page_text = soup.get_text()
            if any(keyword in page_text for keyword in ['상품', '제품', 'product', 'item', '원', '₩', '가격']):
                print(f"[CRAWLER] 페이지에 제품 관련 내용 있음")
                
                # 모든 div 중에서 제품 관련 텍스트가 있는 것 찾기
                all_divs = soup.find_all('div')
                for div in all_divs[:50]:  # 처음 50개만 확인
                    try:
                        text = div.get_text(strip=True)
                        if text and len(text) > 5:
                            # 가격 정보나 제품명이 포함된 div 찾기
                            if any(keyword in text for keyword in ['원', '₩', '가격', 'price', '상품', '제품']):
                                print(f"[CRAWLER] 가격/제품 정보가 있는 div 찾음: {text[:50]}...")
                                return div
                    except:
                        continue
            
            print(f"[CRAWLER] BeautifulSoup으로 제품 요소를 찾을 수 없음")
            return None
            
        except Exception as e:
            print(f"[CRAWLER] BeautifulSoup 제품 요소 찾기 실패: {str(e)}")
            return None
    
    def extract_product_info(self, product_element) -> Optional[Dict]:
        """제품 요소에서 정보 추출 (강화된 방법)"""
        try:
            print(f"[CRAWLER] 제품 정보 추출 시작")
            
            # 제품명 (더 많은 선택자 시도)
            name_selectors = [
                '.name', '.product-name', 'strong', 'span.product-name', 'a[title]',
                'h3', 'h4', 'h5', 'span[class*="name"]', 'div[class*="name"]',
                'a', 'span', 'div'
            ]
            
            product_name = "제품명 없음"
            for selector in name_selectors:
                try:
                    elements = product_element.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        title = element.get_attribute('title') or ''
                        
                        # 제품명으로 적합한 텍스트 찾기
                        if text and len(text) > 2 and len(text) < 100:
                            if not any(skip in text.lower() for skip in ['원', '₩', '가격', 'price', '할인', '쿠폰']):
                                product_name = text
                                print(f"[CRAWLER] 제품명 찾음: {product_name}")
                                break
                        elif title and len(title) > 2 and len(title) < 100:
                            if not any(skip in title.lower() for skip in ['원', '₩', '가격', 'price', '할인', '쿠폰']):
                                product_name = title
                                print(f"[CRAWLER] 제품명 찾음 (title): {product_name}")
                                break
                    
                    if product_name != "제품명 없음":
                        break
                except:
                    continue
            
            # 가격 (더 많은 선택자 시도)
            price_selectors = [
                '.price-value', '.price', '.cost', 'span[data-price]', 'strong.price',
                'span[class*="price"]', 'div[class*="price"]', 'em[class*="price"]',
                'span', 'div', 'strong', 'em'
            ]
            
            price = 0
            for selector in price_selectors:
                try:
                    elements = product_element.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        price_text = element.text.strip()
                        if price_text and price_text != "0":
                            # 숫자만 추출 (가격 패턴)
                            import re
                            # 다양한 가격 패턴 시도
                            price_patterns = [
                                r'[\d,]+원',  # 12,000원
                                r'[\d,]+₩',  # 12,000₩
                                r'[\d,]+',   # 12,000
                                r'[\d]+'     # 12000
                            ]
                            
                            for pattern in price_patterns:
                                price_match = re.search(pattern, price_text)
                                if price_match:
                                    price_str = price_match.group()
                                    # 숫자만 추출
                                    price_num = re.search(r'[\d]+', price_str)
                                    if price_num:
                                        price = int(price_num.group().replace(',', ''))
                                        print(f"[CRAWLER] 가격 찾음: {price}원 (원본: {price_text})")
                                        break
                            
                            if price > 0:
                                break
                    
                    if price > 0:
                        break
                except:
                    continue
            
            # 이미지 URL (더 많은 선택자 시도)
            img_selectors = [
                'img.search-product-wrap-img', 'img[src*="image"]', 'img.product-image', 'img',
                'img[class*="product"]', 'img[class*="item"]', 'img[alt*="상품"]'
            ]
            
            image_url = None
            for selector in img_selectors:
                try:
                    elements = product_element.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        src = element.get_attribute('src')
                        if src and 'http' in src and ('image' in src or 'product' in src):
                            image_url = src
                            print(f"[CRAWLER] 이미지 URL 찾음: {image_url[:50]}...")
                            break
                    
                    if image_url:
                        break
                except:
                    continue
            
            # 제품 상세 페이지 URL (더 많은 선택자 시도)
            link_selectors = [
                'a.search-product-link', 'a[href*="products"]', 'a[href*="item"]', 'a',
                'a[class*="product"]', 'a[class*="item"]', 'a[title]'
            ]
            
            product_url = None
            for selector in link_selectors:
                try:
                    elements = product_element.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        href = element.get_attribute('href')
                        if href and 'coupang.com' in href and ('products' in href or 'item' in href):
                            product_url = href
                            print(f"[CRAWLER] 제품 URL 찾음: {product_url[:50]}...")
                            break
                    
                    if product_url:
                        break
                except:
                    continue
            
            # 할인가 확인
            discount_price = None
            try:
                discount_selectors = [
                    '.price-value.discount', '.discount-price', '.sale-price',
                    'span[class*="discount"]', 'div[class*="discount"]', 'em[class*="discount"]'
                ]
                
                for selector in discount_selectors:
                    try:
                        elements = product_element.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            discount_text = element.text.strip()
                            if discount_text:
                                import re
                                discount_match = re.search(r'[\d,]+', discount_text)
                                if discount_match:
                                    discount_price = int(discount_match.group().replace(',', ''))
                                    print(f"[CRAWLER] 할인가 찾음: {discount_price}원")
                                    break
                        
                        if discount_price:
                            break
                    except:
                        continue
            except:
                pass
            
            print(f"[CRAWLER] 제품 정보 추출 완료: {product_name}, 가격: {price}원")
            
            return {
                'name': product_name,
                'price': price,
                'discount_price': discount_price,
                'image_url': image_url,
                'product_url': product_url,
                'crawled_at': timezone.now()
            }
            
        except Exception as e:
            print(f"[CRAWLER] 제품 정보 추출 실패: {str(e)}")
            return None
    
    def extract_product_info_beautifulsoup(self, product_element) -> Optional[Dict]:
        """BeautifulSoup으로 제품 정보 추출 (실제 크롤링 사례 기반)"""
        try:
            print(f"[CRAWLER] BeautifulSoup 제품 정보 추출 시작")
            
            # 실제 쿠팡 크롤링 사례에서 사용하는 CSS 선택자들
            name_selectors = [
                # 1순위: 실제 작동하는 선택자들
                '.name',
                '.product-name', 
                'strong',
                'span.product-name',
                'a[title]',
                
                # 2순위: 일반적인 제품명 선택자들
                'h3', 'h4', 'h5',
                'span[class*="name"]',
                'div[class*="name"]',
                'a', 'span', 'div',
                
                # 3순위: 새로운 쿠팡 구조
                '.new-product-name',
                '.product-title',
                '[data-testid*="name"]',
                '[data-testid*="title"]'
            ]
            
            product_name = "제품명 없음"
            for selector in name_selectors:
                try:
                    elements = product_element.select(selector)
                    for element in elements:
                        text = element.get_text(strip=True)
                        title = element.get('title') or ''
                        
                        # 제품명으로 적합한 텍스트 찾기
                        if text and len(text) > 2 and len(text) < 100:
                            if not any(skip in text.lower() for skip in ['원', '₩', '가격', 'price', '할인', '쿠폰', '배송', '무료']):
                                product_name = text
                                print(f"[CRAWLER] 제품명 찾음: {product_name}")
                                break
                        elif title and len(title) > 2 and len(title) < 100:
                            if not any(skip in title.lower() for skip in ['원', '₩', '가격', 'price', '할인', '쿠폰', '배송', '무료']):
                                product_name = title
                                print(f"[CRAWLER] 제품명 찾음 (title): {product_name}")
                                break
                    
                    if product_name != "제품명 없음":
                        break
                except:
                    continue
            
            # 가격 추출 (실제 크롤링 사례 기반)
            price_selectors = [
                # 1순위: 실제 작동하는 선택자들
                'span[data-price]',  # data-price 속성 우선
                '.price-value',
                '.price',
                '.cost',
                'strong.price',
                
                # 2순위: 일반적인 가격 선택자들
                'span[class*="price"]',
                'div[class*="price"]',
                'em[class*="price"]',
                'span', 'div', 'strong', 'em',
                
                # 3순위: 새로운 쿠팡 구조
                '.new-product-price',
                '.product-price',
                '[data-testid*="price"]'
            ]
            
            price = 0
            for selector in price_selectors:
                try:
                    elements = product_element.select(selector)
                    for element in elements:
                        # data-price 속성에서 먼저 시도
                        data_price = element.get('data-price') or ''
                        if data_price and data_price.replace(',', '').isdigit():
                            price = int(data_price.replace(',', ''))
                            print(f"[CRAWLER] data-price에서 가격 찾음: {price}원")
                            break
                        
                        # 텍스트에서 가격 추출
                        price_text = element.get_text(strip=True)
                        if price_text and price_text != "0":
                            import re
                            # 다양한 가격 패턴 시도
                            price_patterns = [
                                r'[\d,]+원',  # 12,000원
                                r'[\d,]+₩',  # 12,000₩
                                r'[\d,]+',   # 12,000
                                r'[\d]+'     # 12000
                            ]
                            
                            for pattern in price_patterns:
                                price_match = re.search(pattern, price_text)
                                if price_match:
                                    price_str = price_match.group()
                                    # 숫자만 추출
                                    price_num = re.search(r'[\d]+', price_str)
                                    if price_num:
                                        price = int(price_num.group().replace(',', ''))
                                        print(f"[CRAWLER] 가격 찾음: {price}원 (원본: {price_text})")
                                        break
                            
                            if price > 0:
                                break
                    
                    if price > 0:
                        break
                except:
                    continue
            
            # 이미지 URL 추출 (실제 크롤링 사례 기반)
            img_selectors = [
                # 1순위: 실제 작동하는 선택자들
                'img.search-product-wrap-img',
                'img[src*="image"]',
                'img.product-image',
                'img',
                
                # 2순위: 일반적인 이미지 선택자들
                'img[class*="product"]',
                'img[class*="item"]',
                'img[alt*="상품"]',
                
                # 3순위: 새로운 쿠팡 구조
                '.new-product-image',
                '.product-image',
                'img[src*="product"]',
                
                # 4순위: 지연 로딩 이미지
                'img[data-src]',
                'img[data-lazy-src]'
            ]
            
            image_url = None
            for selector in img_selectors:
                try:
                    elements = product_element.select(selector)
                    for element in elements:
                        # src, data-src, data-lazy-src 순서로 시도
                        src = (element.get('src') or 
                               element.get('data-src') or 
                               element.get('data-lazy-src'))
                        
                        if src and 'http' in src and ('image' in src or 'product' in src):
                            image_url = src
                            print(f"[CRAWLER] 이미지 URL 찾음: {image_url[:50]}...")
                            break
                    
                    if image_url:
                        break
                except:
                    continue
            
            # 제품 상세 페이지 URL 추출 (실제 크롤링 사례 기반)
            link_selectors = [
                # 1순위: 실제 작동하는 선택자들
                'a.search-product-link',
                'a[href*="products"]',
                'a[href*="item"]',
                'a',
                
                # 2순위: 일반적인 링크 선택자들
                'a[class*="product"]',
                'a[class*="item"]',
                'a[title]',
                
                # 3순위: 새로운 쿠팡 구조
                '.new-product-link',
                '.product-link',
                '[data-testid*="link"]'
            ]
            
            product_url = None
            for selector in link_selectors:
                try:
                    elements = product_element.select(selector)
                    for element in elements:
                        href = element.get('href')
                        if href and 'coupang.com' in href and ('products' in href or 'item' in href):
                            product_url = href
                            print(f"[CRAWLER] 제품 URL 찾음: {product_url[:50]}...")
                            break
                    
                    if product_url:
                        break
                except:
                    continue
            
            # 할인가 확인 (실제 크롤링 사례 기반)
            discount_price = None
            try:
                discount_selectors = [
                    # 1순위: 실제 작동하는 선택자들
                    '.price-value.discount',
                    '.discount-price',
                    '.sale-price',
                    
                    # 2순위: 일반적인 할인 선택자들
                    'span[class*="discount"]',
                    'div[class*="discount"]',
                    'em[class*="discount"]',
                    
                    # 3순위: 새로운 쿠팡 구조
                    '[data-testid*="discount"]'
                ]
                
                for selector in discount_selectors:
                    try:
                        elements = product_element.select(selector)
                        for element in elements:
                            discount_text = element.get_text(strip=True)
                            if discount_text:
                                import re
                                discount_match = re.search(r'[\d,]+', discount_text)
                                if discount_match:
                                    discount_price = int(discount_match.group().replace(',', ''))
                                    print(f"[CRAWLER] 할인가 찾음: {discount_price}원")
                                    break
                            
                            if discount_price:
                                break
                    except:
                        continue
            except:
                pass
            
            print(f"[CRAWLER] BeautifulSoup 제품 정보 추출 완료: {product_name}, 가격: {price}원")
            
            return {
                'name': product_name,
                'price': price,
                'discount_price': discount_price,
                'image_url': image_url,
                'product_url': product_url,
                'crawled_at': timezone.now()
            }
            
        except Exception as e:
            print(f"[CRAWLER] BeautifulSoup 제품 정보 추출 실패: {str(e)}")
            return None
    
    def _try_search_selenium(self, search_query: str) -> Optional[Dict]:
        """Selenium을 사용한 백업 검색 (기존 코드 유지)"""
        if not self.driver:
            return None
            
        try:
            # 쿠팡 검색 페이지 접속
            search_url = f"https://www.coupang.com/np/search?q={search_query}"
            print(f"[CRAWLER] Selenium 백업 검색 시도: {search_query}")
            
            self.driver.get(search_url)
            
            # 페이지 로딩 대기
            time.sleep(random.uniform(3, 6))
            
            # 기존 Selenium 로직 사용
            product_element = self._find_product_element_selenium()
            
            if product_element:
                product_info = self.extract_product_info_selenium(product_element)
                if product_info:
                    return product_info
            
            return None
            
        except Exception as e:
            print(f"[CRAWLER] Selenium 백업 검색 실패: {search_query} - {str(e)}")
            return None
    
    def _find_product_element_selenium(self):
        """Selenium으로 제품 요소 찾기 (기존 코드)"""
        try:
            # 1단계: 일반적인 제품 선택자들
            basic_selectors = [
                'li.search-product',
                'div.search-product',
                'div[data-product-id]',
                'div.search-product-wrap',
                'li[data-product-id]',
                'div.product-item',
                'div.product-card'
            ]
            
            for selector in basic_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"[CRAWLER] Selenium으로 제품 요소 {len(elements)}개 찾음: {selector}")
                        return elements[0]  # 첫 번째 제품 반환
                except:
                    continue
            
            # 2단계: 더 일반적인 선택자들
            general_selectors = [
                'div[class*="product"]',
                'li[class*="product"]',
                'div[class*="item"]',
                'div[class*="card"]'
            ]
            
            for selector in general_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        # 제품 관련 클래스를 가진 요소 필터링
                        for element in elements:
                            class_name = element.get_attribute('class') or ''
                            if any(keyword in class_name.lower() for keyword in ['product', 'item', 'card']):
                                print(f"[CRAWLER] Selenium으로 일반 선택자로 제품 요소 찾음: {selector}")
                                return element
                except:
                    continue
            
            # 3단계: 페이지 소스 분석
            page_source = self.driver.page_source
            print(f"[CRAWLER] Selenium 페이지 소스 길이: {len(page_source)}")
            
            # 제품 관련 키워드 확인
            if any(keyword in page_source for keyword in ['상품', '제품', 'product', 'item']):
                print(f"[CRAWLER] Selenium으로 페이지에 제품 관련 내용 있음")
                # 마지막 시도: 모든 div 중에서 제품 관련 텍스트가 있는 것 찾기
                try:
                    all_divs = self.driver.find_elements(By.TAG_NAME, 'div')
                    for div in all_divs[:20]:  # 처음 20개만 확인
                        try:
                            text = div.text.strip()
                            if text and len(text) > 5 and any(keyword in text for keyword in ['원', '₩', '가격', 'price']):
                                print(f"[CRAWLER] Selenium으로 가격 정보가 있는 div 찾음: {text[:50]}...")
                                return div
                        except:
                            continue
                except:
                    pass
            
            print(f"[CRAWLER] Selenium으로 제품 요소를 찾을 수 없음")
            return None
            
        except Exception as e:
            print(f"[CRAWLER] Selenium 제품 요소 찾기 실패: {str(e)}")
            return None
    
    def extract_product_info_selenium(self, product_element) -> Optional[Dict]:
        """Selenium으로 제품 정보 추출 (강화된 버전)"""
        try:
            print(f"[CRAWLER] Selenium 제품 정보 추출 시작")
            
            # 제품명 (더 정확한 선택자들)
            name_selectors = [
                'a[title]',  # 링크의 title 속성
                '.name', '.product-name', 'strong', 'span.product-name',
                'h3', 'h4', 'h5', 'span[class*="name"]', 'div[class*="name"]',
                'a', 'span', 'div', '.new-product-name', '.product-title',
                '[data-testid*="name"]', '[data-testid*="title"]'  # 테스트 ID 기반
            ]
            
            product_name = "제품명 없음"
            for selector in name_selectors:
                try:
                    elements = product_element.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        title = element.get_attribute('title') or ''
                        
                        # 제품명으로 적합한 텍스트 찾기
                        if text and len(text) > 2 and len(text) < 100:
                            if not any(skip in text.lower() for skip in ['원', '₩', '가격', 'price', '할인', '쿠폰', '배송', '무료']):
                                product_name = text
                                print(f"[CRAWLER] Selenium으로 제품명 찾음: {product_name}")
                                break
                        elif title and len(title) > 2 and len(title) < 100:
                            if not any(skip in title.lower() for skip in ['원', '₩', '가격', 'price', '할인', '쿠폰', '배송', '무료']):
                                product_name = title
                                print(f"[CRAWLER] Selenium으로 제품명 찾음 (title): {product_name}")
                                break
                    
                    if product_name != "제품명 없음":
                        break
                except:
                    continue
            
            # 가격 (더 정확한 선택자들)
            price_selectors = [
                'span[data-price]',  # data-price 속성
                '.price-value', '.price', '.cost', 'strong.price',
                'span[class*="price"]', 'div[class*="price"]', 'em[class*="price"]',
                'span', 'div', 'strong', 'em', '.new-product-price', '.product-price',
                '[data-testid*="price"]'  # 테스트 ID 기반
            ]
            
            price = 0
            for selector in price_selectors:
                try:
                    elements = product_element.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        price_text = element.text.strip()
                        data_price = element.get_attribute('data-price') or ''
                        
                        # data-price 속성에서 먼저 시도
                        if data_price and data_price.isdigit():
                            price = int(data_price)
                            print(f"[CRAWLER] Selenium으로 data-price에서 가격 찾음: {price}원")
                            break
                        
                        # 텍스트에서 가격 추출
                        if price_text and price_text != "0":
                            import re
                            # 다양한 가격 패턴 시도
                            price_patterns = [
                                r'[\d,]+원',  # 12,000원
                                r'[\d,]+₩',  # 12,000₩
                                r'[\d,]+',   # 12,000
                                r'[\d]+'     # 12000
                            ]
                            
                            for pattern in price_patterns:
                                price_match = re.search(pattern, price_text)
                                if price_match:
                                    price_str = price_match.group()
                                    # 숫자만 추출
                                    price_num = re.search(r'[\d]+', price_str)
                                    if price_num:
                                        price = int(price_num.group().replace(',', ''))
                                        print(f"[CRAWLER] Selenium으로 가격 찾음: {price}원 (원본: {price_text})")
                                        break
                            
                            if price > 0:
                                break
                    
                    if price > 0:
                        break
                except:
                    continue
            
            # 이미지 URL (더 정확한 선택자들)
            img_selectors = [
                'img[src*="image"]', 'img.search-product-wrap-img', 'img.product-image', 'img',
                'img[class*="product"]', 'img[class*="item"]', 'img[alt*="상품"]',
                'img[data-src]', 'img[data-lazy-src]'  # 지연 로딩 이미지
            ]
            
            image_url = None
            for selector in img_selectors:
                try:
                    elements = product_element.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        src = element.get_attribute('src') or element.get_attribute('data-src') or element.get_attribute('data-lazy-src')
                        if src and 'http' in src and ('image' in src or 'product' in src):
                            image_url = src
                            print(f"[CRAWLER] Selenium으로 이미지 URL 찾음: {image_url[:50]}...")
                            break
                    
                    if image_url:
                        break
                except:
                    continue
            
            # 제품 상세 페이지 URL (더 정확한 선택자들)
            link_selectors = [
                'a[href*="products"]', 'a[href*="item"]', 'a.search-product-link',
                'a[class*="product"]', 'a[class*="item"]', 'a[title]',
                'a[data-testid*="link"]'  # 테스트 ID 기반
            ]
            
            product_url = None
            for selector in link_selectors:
                try:
                    elements = product_element.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        href = element.get_attribute('href')
                        if href and 'coupang.com' in href and ('products' in href or 'item' in href):
                            product_url = href
                            print(f"[CRAWLER] 제품 URL 찾음: {product_url[:50]}...")
                            break
                    
                    if product_url:
                        break
                except:
                    continue
            
            # 할인가 확인
            discount_price = None
            try:
                discount_selectors = [
                    '.price-value.discount', '.discount-price', '.sale-price',
                    'span[class*="discount"]', 'div[class*="discount"]', 'em[class*="discount"]',
                    '[data-testid*="discount"]'  # 테스트 ID 기반
                ]
                
                for selector in discount_selectors:
                    try:
                        elements = product_element.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            discount_text = element.text.strip()
                            if discount_text:
                                import re
                                discount_match = re.search(r'[\d,]+', discount_text)
                                if discount_match:
                                    discount_price = int(discount_match.group().replace(',', ''))
                                    print(f"[CRAWLER] Selenium으로 할인가 찾음: {discount_price}원")
                                    break
                            
                            if discount_price:
                                break
                    except:
                        continue
            except:
                pass
            
            print(f"[CRAWLER] Selenium 제품 정보 추출 완료: {product_name}, 가격: {price}원")
            
            return {
                'name': product_name,
                'price': price,
                'discount_price': discount_price,
                'image_url': image_url,
                'product_url': product_url,
                'crawled_at': timezone.now()
            }
            
        except Exception as e:
            print(f"[CRAWLER] Selenium 제품 정보 추출 실패: {str(e)}")
            return None
    
    def crawl_food_prices(self, food: Food, retry_count: int = 0) -> Optional[Dict]:
        """특정 식품의 가격 정보 크롤링 (재검색 지원)"""
        try:
            print(f"[CRAWLER] 식품 크롤링 시작: {food.food_name} ({food.company_name}) - 재시도: {retry_count}")
            
            # 기본 검색 시도
            product_info = self.search_product(food.food_name, food.company_name)
            
            if product_info:
                # Price 테이블에 저장할 데이터 구성
                price_data = {
                    'food': food,
                    'shop_name': '쿠팡',
                    'price': product_info['price'],
                    'discount_price': product_info['discount_price'],
                    'product_image_url': product_info['image_url'],
                    'product_url': product_info['product_url'],
                    'crawled_at': product_info['crawled_at'],
                    'crawling_status': 'success',
                    'is_available': True
                }
                
                print(f"[CRAWLER] 크롤링 성공: {food.food_name} - {product_info['price']}원")
                return price_data
            
            # 기본 검색 실패 시 재검색 시도
            if retry_count < 2:  # 최대 2번까지 재시도
                print(f"[CRAWLER] 기본 검색 실패, 재검색 시도 {retry_count + 1}/2")
                
                # 이전에 시도한 검색어들 (기본 검색에서 사용된 것들)
                previous_attempts = [
                    f"{food.food_name} {food.company_name}" if food.company_name else None,
                    food.food_name,
                    food.company_name if food.company_name else None
                ]
                previous_attempts = [q for q in previous_attempts if q]
                
                # 재검색 실행
                retry_result = self.retry_search_product(
                    food.food_name, 
                    food.company_name, 
                    previous_attempts
                )
                
                if retry_result:
                    # 재검색 성공
                    price_data = {
                        'food': food,
                        'shop_name': '쿠팡',
                        'price': retry_result['price'],
                        'discount_price': retry_result['discount_price'],
                        'product_image_url': retry_result['image_url'],
                        'product_url': retry_result['product_url'],
                        'crawled_at': retry_result['crawled_at'],
                        'crawling_status': 'success',
                        'is_available': True
                    }
                    
                    print(f"[CRAWLER] 재검색 성공: {food.food_name} - {retry_result['price']}원")
                    return price_data
                else:
                    # 재검색도 실패 시 재귀적으로 한 번 더 시도
                    if retry_count < 1:
                        print(f"[CRAWLER] 재검색 실패, 최종 재시도")
                        return self.crawl_food_prices(food, retry_count + 1)
            
            # 모든 검색 시도 실패
            print(f"[CRAWLER] 제품을 찾을 수 없음: {food.food_name}")
            return {
                'food': food,
                'shop_name': '쿠팡',
                'price': 0,
                'crawling_status': 'not_found',
                'crawled_at': timezone.now(),
                'is_available': False
            }
                
        except Exception as e:
            print(f"[CRAWLER] 크롤링 실패: {food.food_name} - {str(e)}")
            return {
                'food': food,
                'shop_name': '쿠팡',
                'price': 0,
                'crawling_status': 'failed',
                'crawling_error': str(e),
                'crawled_at': timezone.now(),
                'is_available': False
            }
    
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            print("[CRAWLER] Chrome 드라이버 종료")


def batch_crawl_food_prices(food_ids: list, headless: bool = True) -> Dict:
    """여러 식품의 가격 정보를 일괄 크롤링 (재검색 지원)"""
    crawler = None
    results = {
        'total': len(food_ids),
        'success': 0,
        'retry_success': 0,  # 재검색으로 성공한 경우
        'failed': 0,
        'not_found': 0,
        'details': []
    }
    
    try:
        crawler = CoupangCrawler(headless=headless)
        
        for i, food_id in enumerate(food_ids):
            try:
                food = Food.objects.get(food_id=food_id)
                print(f"[BATCH_CRAWLER] 진행률: {i+1}/{len(food_ids)} - {food.food_name}")
                
                # 크롤링 실행
                price_data = crawler.crawl_food_prices(food)
                
                if price_data:
                    # Price 테이블에 저장
                    price_id = f"P{datetime.now().strftime('%Y%m%d')}{str(i+1).zfill(4)}"
                    
                    price_obj, created = Price.objects.update_or_create(
                        food=food,
                        shop_name='쿠팡',
                        defaults={
                            'price_id': price_id,
                            'price': price_data['price'],
                            'discount_price': price_data.get('discount_price'),
                            'product_image_url': price_data.get('product_image_url'),
                            'product_url': price_data.get('product_url'),
                            'crawled_at': price_data['crawled_at'],
                            'crawling_status': price_data['crawling_status'],
                            'crawling_error': price_data.get('crawling_error'),
                            'is_available': price_data['is_available']
                        }
                    )
                    
                    # 결과 업데이트
                    if price_data['crawling_status'] == 'success':
                        # 재검색으로 성공했는지 확인 (가격이 0이 아니고 제품 정보가 있음)
                        if price_data['price'] > 0 and price_data.get('product_url'):
                            # 이전에 not_found 상태였는지 확인
                            previous_price = Price.objects.filter(
                                food=food, 
                                shop_name='쿠팡'
                            ).exclude(pk=price_obj.pk).first()
                            
                            if previous_price and previous_price.crawling_status in ['not_found', 'failed']:
                                results['retry_success'] += 1
                                print(f"[BATCH_CRAWLER] 재검색으로 성공: {food.food_name}")
                            else:
                                results['success'] += 1
                        else:
                            results['success'] += 1
                    elif price_data['crawling_status'] == 'not_found':
                        results['not_found'] += 1
                    else:
                        results['failed'] += 1
                    
                    results['details'].append({
                        'food_id': food_id,
                        'food_name': food.food_name,
                        'status': price_data['crawling_status'],
                        'price': price_data['price'],
                        'created': created,
                        'retry_success': price_data['crawling_status'] == 'success' and price_data['price'] > 0
                    })
                
                # 크롤링 간격 조절 (쿠팡 차단 방지)
                time.sleep(random.uniform(3, 7))
                
            except Food.DoesNotExist:
                print(f"[BATCH_CRAWLER] 식품을 찾을 수 없음: {food_id}")
                results['failed'] += 1
                results['details'].append({
                    'food_id': food_id,
                    'status': 'food_not_found',
                    'error': '식품 정보를 찾을 수 없음'
                })
                
            except Exception as e:
                print(f"[BATCH_CRAWLER] 크롤링 오류: {food_id} - {str(e)}")
                results['failed'] += 1
                results['details'].append({
                    'food_id': food_id,
                    'status': 'error',
                    'error': str(e)
                })
    
    except Exception as e:
        print(f"[BATCH_CRAWLER] 일괄 크롤링 실패: {str(e)}")
        results['error'] = str(e)
    
    finally:
        if crawler:
            crawler.close()
    
    print(f"[BATCH_CRAWLER] 완료: 성공 {results['success']}, 재검색 성공 {results['retry_success']}, 실패 {results['failed']}, 없음 {results['not_found']}")
    return results
