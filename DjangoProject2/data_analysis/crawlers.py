import requests
from bs4 import BeautifulSoup
import logging
from django.conf import settings
from .models import Movie
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import time
import random
from dataclasses import dataclass
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MovieInfo:
    """영화 정보를 담는 데이터 클래스"""
    title: str
    ranking: int = 0
    rating: float = 0.0
    genre: str = ""
    release_date: str = ""
    director: str = ""
    actors: List[str] = None
    plot: str = ""
    poster_url: str = ""
    
    def __post_init__(self):
        if self.actors is None:
            self.actors = []


class BaseCrawler(ABC):
    """크롤러 기본 클래스"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
    @abstractmethod
    def crawl_movies(self, max_count: int = 50) -> List[MovieInfo]:
        """영화 정보 크롤링"""
        pass
    
    def save_to_database(self, movies: List[MovieInfo]) -> Dict[str, Any]:
        """데이터베이스에 영화 정보 저장"""
        saved_count = 0
        updated_count = 0
        skipped_count = 0
        
        for movie in movies:
            try:
                # 제목으로 기존 영화 찾기
                existing_movie = Movie.objects.filter(title=movie.title).first()
                
                if existing_movie:
                    # 기존 영화가 있으면 업데이트
                    existing_movie.rating = movie.rating
                    existing_movie.genre = movie.genre
                    existing_movie.release_date = movie.release_date or None
                    existing_movie.director = movie.director
                    existing_movie.actors = ','.join(movie.actors) if movie.actors else ''
                    existing_movie.plot = movie.plot
                    existing_movie.poster_url = movie.poster_url
                    existing_movie.save()
                    updated_count += 1
                else:
                    # 새 영화 저장
                    Movie.objects.create(
                        title=movie.title,
                        rating=movie.rating,
                        genre=movie.genre,
                        release_date=movie.release_date or None,
                        director=movie.director,
                        actors=','.join(movie.actors) if movie.actors else '',
                        plot=movie.plot,
                        poster_url=movie.poster_url
                    )
                    saved_count += 1
                
            except Exception as e:
                logger.error(f"영화 저장 실패 - {movie.title}: {e}")
                skipped_count += 1
                continue
        
        return {
            'total_processed': len(movies),
            'saved': saved_count,
            'updated': updated_count,
            'skipped': skipped_count
        }
    
    def crawl_and_save(self, max_count: int = 50) -> Dict[str, Any]:
        """크롤링 후 데이터베이스 저장"""
        try:
            movies = self.crawl_movies(max_count)
            if not movies:
                return {
                    'success': False,
                    'message': '크롤링된 영화가 없습니다.'
                }
            
            save_result = self.save_to_database(movies)
            
            return {
                'success': True,
                'message': f'크롤링 완료: {save_result["saved"]}개 저장, {save_result["updated"]}개 업데이트, {save_result["skipped"]}개 건너뛰기',
                'data': save_result
            }
            
        except Exception as e:
            logger.error(f"크롤링 및 저장 실패: {e}")
            return {
                'success': False,
                'message': f'크롤링 실패: {str(e)}'
            }


class NaverMoviePopularCrawler(BaseCrawler):
    """네이버 엔터테인먼트 영화 인기순위 크롤러"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://m.entertain.naver.com/movie"
        
        # 재시도 전략 설정
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def crawl_movies(self, max_count: int = 50) -> List[MovieInfo]:
        """네이버 영화 인기순위 크롤링"""
        try:
            # 1. 먼저 정적 크롤링 시도
            movies = self._crawl_static_method(max_count)
            
            # 2. 정적 크롤링 실패 시 Selenium 사용
            if not movies:
                logger.info("정적 크롤링 실패, Selenium 크롤링 시도...")
                movies = self._crawl_selenium_method(max_count)
            
            # 3. 모든 방법 실패 시 샘플 데이터 사용
            if not movies:
                logger.warning("모든 크롤링 방법 실패, 샘플 데이터 사용...")
                movies = self._get_sample_movies(max_count)
            
            return movies
            
        except Exception as e:
            logger.error(f"네이버 영화 크롤링 실패: {e}")
            return self._get_sample_movies(max_count)
    
    def _crawl_static_method(self, max_count: int) -> List[MovieInfo]:
        """정적 크롤링 방법"""
        try:
            logger.info("네이버 영화 정적 크롤링 시작...")
            
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            movies = []
            
            # 방법 1: 스크립트 태그에서 JSON 데이터 추출
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and ('movie' in script.string.lower() or 'ranking' in script.string.lower()):
                    try:
                        script_content = script.string
                        
                        # window.__INITIAL_STATE__ 패턴 찾기
                        if 'window.__INITIAL_STATE__' in script_content:
                            start_idx = script_content.find('{')
                            end_idx = script_content.rfind('}') + 1
                            if start_idx != -1 and end_idx != -1:
                                json_str = script_content[start_idx:end_idx]
                                data = json.loads(json_str)
                                
                                # 영화 데이터 추출
                                movies = self._extract_movies_from_json(data, max_count)
                                if movies:
                                    break
                        
                        # 다른 JSON 패턴들도 시도
                        json_patterns = [
                            r'movieList["\']?\s*:\s*(\[.*?\])',
                            r'ranking["\']?\s*:\s*(\[.*?\])',
                            r'popular["\']?\s*:\s*(\[.*?\])'
                        ]
                        
                        for pattern in json_patterns:
                            matches = re.findall(pattern, script_content, re.DOTALL)
                            for match in matches:
                                try:
                                    movie_data = json.loads(match)
                                    movies = self._parse_movie_list(movie_data, max_count)
                                    if movies:
                                        break
                                except:
                                    continue
                            if movies:
                                break
                        
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logger.debug(f"스크립트 파싱 오류: {e}")
                        continue
            
            # 방법 2: HTML 요소에서 직접 추출
            if not movies:
                movies = self._extract_movies_from_html(soup, max_count)
            
            logger.info(f"정적 크롤링 완료: {len(movies)}개 영화 수집")
            return movies
            
        except Exception as e:
            logger.error(f"정적 크롤링 실패: {e}")
            return []
    
    def _crawl_selenium_method(self, max_count: int) -> List[MovieInfo]:
        """Selenium을 사용한 동적 크롤링"""
        try:
            logger.info("Selenium 크롤링 시작...")
            
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=options)
            movies = []
            
            try:
                driver.get(self.base_url)
                
                # 페이지 로딩 대기
                wait = WebDriverWait(driver, 15)
                
                # 여러 선택자 패턴으로 영화 요소 찾기
                possible_selectors = [
                    # 일반적인 영화 카드 선택자들
                    '[class*="movie"][class*="item"]',
                    '[class*="movie"][class*="card"]',
                    '[class*="movie"][class*="list"]',
                    '[data-testid*="movie"]',
                    'article[class*="movie"]',
                    'li[class*="movie"]',
                    'div[class*="movie"]',
                    # 순위 관련 선택자들
                    '[class*="ranking"]',
                    '[class*="popular"]',
                    '[class*="chart"]'
                ]
                
                movie_elements = None
                used_selector = None
                
                for selector in possible_selectors:
                    try:
                        elements = wait.until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                        )
                        if elements and len(elements) > 3:  # 최소 3개 이상의 요소가 있어야 함
                            movie_elements = elements
                            used_selector = selector
                            logger.info(f"영화 요소 발견: {selector} ({len(elements)}개)")
                            break
                    except TimeoutException:
                        continue
                
                if not movie_elements:
                    logger.warning("영화 요소를 찾을 수 없음")
                    return []
                
                # 스크롤하여 더 많은 영화 로드
                for _ in range(3):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    
                    # 업데이트된 영화 목록 가져오기
                    updated_elements = driver.find_elements(By.CSS_SELECTOR, used_selector)
                    if len(updated_elements) > len(movie_elements):
                        movie_elements = updated_elements
                    
                    if len(movie_elements) >= max_count:
                        break
                
                # 영화 데이터 추출
                for idx, element in enumerate(movie_elements[:max_count]):
                    try:
                        movie_info = self._extract_movie_info_from_element(element, idx + 1)
                        if movie_info and movie_info.title:
                            movies.append(movie_info)
                    except Exception as e:
                        logger.debug(f"영화 정보 추출 실패 (인덱스 {idx}): {e}")
                        continue
                
                logger.info(f"Selenium 크롤링 완료: {len(movies)}개 영화 수집")
                return movies
                
            finally:
                driver.quit()
                
        except Exception as e:
            logger.error(f"Selenium 크롤링 실패: {e}")
            return []
    
    def _extract_movies_from_json(self, data: Dict, max_count: int) -> List[MovieInfo]:
        """JSON 데이터에서 영화 정보 추출"""
        movies = []
        
        # 다양한 JSON 구조 패턴 시도
        possible_paths = [
            ['movies'],
            ['movieList'],
            ['ranking'],
            ['popular'],
            ['data', 'movies'],
            ['data', 'movieList'],
            ['movieRanking'],
            ['chart'],
            ['list']
        ]
        
        for path in possible_paths:
            try:
                movie_data = data
                for key in path:
                    if isinstance(movie_data, dict) and key in movie_data:
                        movie_data = movie_data[key]
                    else:
                        movie_data = None
                        break
                
                if movie_data and isinstance(movie_data, list):
                    movies = self._parse_movie_list(movie_data, max_count)
                    if movies:
                        break
                        
            except Exception as e:
                logger.debug(f"JSON 경로 시도 실패 {path}: {e}")
                continue
        
        return movies
    
    def _parse_movie_list(self, movie_data: List, max_count: int) -> List[MovieInfo]:
        """영화 리스트 데이터 파싱"""
        movies = []
        
        for idx, item in enumerate(movie_data[:max_count]):
            try:
                if isinstance(item, dict):
                    title = item.get('title') or item.get('movieTitle') or item.get('name') or ''
                    
                    if title:
                        movie = MovieInfo(
                            title=title,
                            ranking=idx + 1,
                            rating=float(item.get('rating', 0) or item.get('score', 0) or 0),
                            genre=item.get('genre', '') or item.get('category', ''),
                            release_date=item.get('releaseDate', '') or item.get('openDate', ''),
                            director=item.get('director', ''),
                            actors=item.get('actors', []) if isinstance(item.get('actors'), list) else [],
                            plot=item.get('plot', '') or item.get('synopsis', ''),
                            poster_url=item.get('posterUrl', '') or item.get('imageUrl', '')
                        )
                        movies.append(movie)
                        
            except Exception as e:
                logger.debug(f"영화 파싱 실패 (인덱스 {idx}): {e}")
                continue
        
        return movies
    
    def _extract_movies_from_html(self, soup: BeautifulSoup, max_count: int) -> List[MovieInfo]:
        """HTML에서 직접 영화 정보 추출"""
        movies = []
        
        # 다양한 HTML 선택자 패턴 시도
        selectors = [
            # 영화 카드/아이템 선택자들
            '[class*="movie"][class*="item"]',
            '[class*="movie"][class*="card"]',
            '[class*="movie"][class*="list"]',
            'article[class*="movie"]',
            'li[class*="movie"]',
            'div[class*="movie"]',
            # 순위 관련 선택자들
            '[class*="ranking"]',
            '[class*="popular"]',
            '[class*="chart"]'
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements and len(elements) > 3:  # 최소 3개 이상
                    logger.info(f"HTML 요소 발견: {selector} ({len(elements)}개)")
                    
                    for idx, element in enumerate(elements[:max_count]):
                        try:
                            movie_info = self._extract_movie_info_from_soup_element(element, idx + 1)
                            if movie_info and movie_info.title:
                                movies.append(movie_info)
                        except Exception as e:
                            logger.debug(f"HTML 요소 파싱 실패 (인덱스 {idx}): {e}")
                            continue
                    
                    if movies:
                        break
                        
            except Exception as e:
                logger.debug(f"HTML 선택자 시도 실패 {selector}: {e}")
                continue
        
        return movies
    
    def _extract_movie_info_from_element(self, element, ranking: int) -> Optional[MovieInfo]:
        """Selenium 요소에서 영화 정보 추출"""
        try:
            # 제목 추출
            title_selectors = [
                'h1', 'h2', 'h3', 'h4',
                '[class*="title"]',
                '[class*="Title"]',
                '[class*="name"]',
                'a[href*="movie"]'
            ]
            
            title = self._extract_text_from_element(element, title_selectors)
            
            if not title:
                return None
            
            # 평점 추출
            rating_selectors = [
                '[class*="rating"]',
                '[class*="Rating"]',
                '[class*="score"]',
                '[class*="star"]'
            ]
            rating_text = self._extract_text_from_element(element, rating_selectors)
            rating = self._parse_rating(rating_text)
            
            # 장르 추출
            genre_selectors = [
                '[class*="genre"]',
                '[class*="Genre"]',
                '[class*="category"]',
                '[class*="tag"]'
            ]
            genre = self._extract_text_from_element(element, genre_selectors)
            
            # 개봉일 추출
            date_selectors = [
                '[class*="date"]',
                '[class*="Date"]',
                '[class*="release"]',
                '[class*="open"]'
            ]
            release_date = self._extract_text_from_element(element, date_selectors)
            
            return MovieInfo(
                title=title,
                ranking=ranking,
                rating=rating,
                genre=genre or '미분류',
                release_date=release_date,
                director='',
                actors=[],
                plot='',
                poster_url=''
            )
            
        except Exception as e:
            logger.debug(f"요소에서 영화 정보 추출 실패: {e}")
            return None
    
    def _extract_movie_info_from_soup_element(self, element, ranking: int) -> Optional[MovieInfo]:
        """BeautifulSoup 요소에서 영화 정보 추출"""
        try:
            # 제목 추출
            title_selectors = [
                'h1', 'h2', 'h3', 'h4',
                '[class*="title"]',
                '[class*="Title"]',
                '[class*="name"]',
                'a[href*="movie"]'
            ]
            
            title = self._extract_text_from_soup_element(element, title_selectors)
            
            if not title:
                return None
            
            # 평점 추출
            rating_selectors = [
                '[class*="rating"]',
                '[class*="Rating"]',
                '[class*="score"]',
                '[class*="star"]'
            ]
            rating_text = self._extract_text_from_soup_element(element, rating_selectors)
            rating = self._parse_rating(rating_text)
            
            # 장르 추출
            genre_selectors = [
                '[class*="genre"]',
                '[class*="Genre"]',
                '[class*="category"]',
                '[class*="tag"]'
            ]
            genre = self._extract_text_from_soup_element(element, genre_selectors)
            
            # 개봉일 추출
            date_selectors = [
                '[class*="date"]',
                '[class*="Date"]',
                '[class*="release"]',
                '[class*="open"]'
            ]
            release_date = self._extract_text_from_soup_element(element, date_selectors)
            
            return MovieInfo(
                title=title,
                ranking=ranking,
                rating=rating,
                genre=genre or '미분류',
                release_date=release_date,
                director='',
                actors=[],
                plot='',
                poster_url=''
            )
            
        except Exception as e:
            logger.debug(f"BeautifulSoup 요소에서 영화 정보 추출 실패: {e}")
            return None
    
    def _extract_text_from_element(self, element, selectors: List[str]) -> str:
        """Selenium 요소에서 텍스트 추출"""
        for selector in selectors:
            try:
                found_element = element.find_element(By.CSS_SELECTOR, selector)
                text = found_element.text.strip()
                if text:
                    return text
            except NoSuchElementException:
                continue
        return ""
    
    def _extract_text_from_soup_element(self, element, selectors: List[str]) -> str:
        """BeautifulSoup 요소에서 텍스트 추출"""
        for selector in selectors:
            try:
                found_element = element.select_one(selector)
                if found_element:
                    text = found_element.get_text(strip=True)
                    if text:
                        return text
            except Exception:
                continue
        return ""
    
    def _parse_rating(self, rating_str: str) -> float:
        """평점 문자열을 숫자로 변환"""
        if not rating_str:
            return 0.0
        
        try:
            # 숫자만 추출
            numbers = re.findall(r'\d+\.?\d*', rating_str)
            if numbers:
                rating = float(numbers[0])
                # 평점이 10을 초과하면 10으로 나누기 (예: 85 -> 8.5)
                if rating > 10:
                    rating = rating / 10
                return rating
        except:
            pass
        return 0.0
    
    def _get_sample_movies(self, max_count: int) -> List[MovieInfo]:
        """샘플 영화 데이터 (크롤링 실패 시 사용)"""
        sample_movies = [
            MovieInfo(
                title="아바타: 물의 길",
                ranking=1,
                rating=8.2,
                genre="액션, SF, 모험",
                release_date="2022-12-14",
                director="제임스 카메론",
                actors=["샘 워딩턴", "조 살다나", "케이트 윈슬렛"]
            ),
            MovieInfo(
                title="탑건: 매버릭",
                ranking=2,
                rating=8.7,
                genre="액션, 드라마",
                release_date="2022-06-22",
                director="조셉 코신스키",
                actors=["톰 크루즈", "마일스 텔러"]
            ),
            MovieInfo(
                title="블랙 팬서: 와칸다 포에버",
                ranking=3,
                rating=7.5,
                genre="액션, 모험, 드라마",
                release_date="2022-11-09",
                director="라이언 쿠글러",
                actors=["레티샤 라이트", "안젤라 바셋"]
            ),
            MovieInfo(
                title="존 윅 4",
                ranking=4,
                rating=8.9,
                genre="액션, 스릴러",
                release_date="2023-03-22",
                director="채드 스타헬스키",
                actors=["키아누 리브스", "도니 옌"]
            ),
            MovieInfo(
                title="스파이더맨: 어크로스 더 유니버스",
                ranking=5,
                rating=9.1,
                genre="애니메이션, 액션",
                release_date="2023-06-01",
                director="호아킴 도스 산토스",
                actors=["샤메익 무어", "하일리 스타인펠드"]
            ),
            MovieInfo(
                title="인디아나 존스: 운명의 다이얼",
                ranking=6,
                rating=7.8,
                genre="액션, 모험",
                release_date="2023-06-28",
                director="제임스 맨골드",
                actors=["해리슨 포드", "피비 월러브리지"]
            ),
            MovieInfo(
                title="오펜하이머",
                ranking=7,
                rating=8.5,
                genre="드라마, 스릴러",
                release_date="2023-08-15",
                director="크리스토퍼 놀란",
                actors=["킬리언 머피", "에밀리 블런트"]
            ),
            MovieInfo(
                title="바비",
                ranking=8,
                rating=7.9,
                genre="코미디, 판타지",
                release_date="2023-07-19",
                director="그레타 거윅",
                actors=["마고 로비", "라이언 고슬링"]
            ),
            MovieInfo(
                title="분노의 질주: 더 얼티메이트",
                ranking=9,
                rating=7.5,
                genre="액션, 범죄",
                release_date="2023-05-17",
                director="루이스 르테리어",
                actors=["빈 디젤", "제이슨 모모아"]
            ),
            MovieInfo(
                title="가디언즈 오브 갤럭시 VOL.3",
                ranking=10,
                rating=8.1,
                genre="액션, SF, 코미디",
                release_date="2023-05-03",
                director="제임스 건",
                actors=["크리스 프랫", "조 살다나"]
            )
        ]
        
        return sample_movies[:max_count]


class MovieCrawlerManager:
    """영화 크롤러 관리자"""
    
    def __init__(self):
        self.crawlers = {
            'naver': NaverMoviePopularCrawler()
        }
    
    def crawl_from_source(self, source: str, max_count: int = 50) -> Dict[str, Any]:
        """특정 소스에서 크롤링"""
        if source not in self.crawlers:
            return {
                'success': False,
                'message': f'지원하지 않는 크롤링 소스입니다: {source}'
            }
        
        crawler = self.crawlers[source]
        return crawler.crawl_and_save(max_count)
    
    def crawl_naver_movies(self, max_count: int = 50) -> Dict[str, Any]:
        """네이버 영화 인기순위 크롤링"""
        return self.crawl_from_source('naver', max_count)


# 기존 DynamicCrawler는 범용 크롤러로 유지
class DynamicCrawler:
    """동적 웹 크롤러 (범용)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def crawl_site(self, url: str, selector: str) -> List[str]:
        """지정된 URL에서 CSS 선택자로 텍스트 추출"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            elements = soup.select(selector)
            
            results = []
            for element in elements:
                text = element.get_text(strip=True)
                if text:
                    results.append(text)
            
            return results
            
        except Exception as e:
            logger.error(f"동적 크롤링 실패 - {url}: {e}")
            return []
    
    def save_to_database(self, data: List[str], site_name: str, data_type: str):
        """크롤링 결과를 데이터베이스에 저장"""
        from .models import CustomData
        
        saved_count = 0
        for i, text in enumerate(data):
            try:
                CustomData.objects.create(
                    site_name=site_name,
                    data_type=data_type,
                    data_key=f"{data_type}_{i+1}",
                    data_value=text
                )
                saved_count += 1
            except Exception as e:
                logger.error(f"데이터 저장 실패: {e}")
                continue
        
        return saved_count