import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import io
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.core.serializers import serialize
from django.db.models import Count
from django.db import models
from .models import Movie, CustomData, MapLocation, TextAnalysis, WordFrequency, create_wordcloud_directly

import json
import logging
from datetime import datetime, timedelta
from collections import Counter
import re
import folium

# ... (기존 import 부분은 그대로)

from .crawlers import MovieCrawlerManager, DynamicCrawler

logger = logging.getLogger(__name__)

def dashboard(request):
    """대시보드 메인 페이지"""
    try:
        # 각 데이터 소스별 통계
        movie_count = Movie.objects.count()
        custom_data_count = CustomData.objects.count()
        map_location_count = MapLocation.objects.count()
        text_analysis_count = TextAnalysis.objects.count()

        # 최근 데이터 수집 정보
        recent_movies = Movie.objects.order_by('-crawled_at')[:5]
        recent_custom_data = CustomData.objects.order_by('-crawled_at')[:5]
        recent_analyses = TextAnalysis.objects.order_by('-created_at')[:5]

        context = {
            'movie_count': movie_count,
            'custom_data_count': custom_data_count,
            'map_location_count': map_location_count,
            'text_analysis_count': text_analysis_count,
            'recent_movies': recent_movies,
            'recent_custom_data': recent_custom_data,
            'recent_analyses': recent_analyses,
        }

        return render(request, 'data_analysis/dashboard.html', context)
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return render(request, 'data_analysis/dashboard.html', {'error': str(e)})

def movie_visualization(request):
    """영화 데이터 시각화 페이지"""
    try:
        # 영화 데이터 가져오기
        movies = Movie.objects.all().order_by('-crawled_at')

        # 기본 통계
        total_movies = movies.count()

        # 평점 데이터 수집
        rating_data = [movie.rating for movie in movies if movie.rating is not None]

        # 통계 계산
        stats = {
            'mean': 0.0,
            'median': 0.0,
            'max': 0.0,
            'min': 0.0,
            'std': 0.0
        }

        if rating_data:
            stats = {
                'mean': round(sum(rating_data) / len(rating_data), 2),
                'median': round(np.median(rating_data), 2),
                'max': round(max(rating_data), 2),
                'min': round(min(rating_data), 2),
                'std': round(np.std(rating_data), 2)
            }

        # 장르별 분포
        genre_data = []
        for movie in movies:
            if movie.genre:
                genres = movie.genre.split(',')
                for genre in genres:
                    genre_data.append(genre.strip())

        genre_counts = Counter(genre_data)

        # 차트 생성
        rating_chart_url = None
        genre_chart_url = None

        # 평점 분포 히스토그램
        if rating_data:
            plt.figure(figsize=(10, 6))
            plt.hist(rating_data, bins=20, edgecolor='black', alpha=0.7)
            plt.title('영화 평점 분포')
            plt.xlabel('평점')
            plt.ylabel('영화 수')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()

            # 이미지를 base64로 변환
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150)
            img_buffer.seek(0)
            rating_chart_url = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close()

        # 장르별 영화 수 막대 그래프
        if genre_counts:
            plt.figure(figsize=(12, 6))
            top_genres = genre_counts.most_common(10)
            genres, counts = zip(*top_genres)

            plt.bar(genres, counts, color='skyblue', edgecolor='black')
            plt.title('장르별 영화 수 (상위 10개)')
            plt.xlabel('장르')
            plt.ylabel('영화 수')
            plt.xticks(rotation=45)
            plt.tight_layout()

            # 이미지를 base64로 변환
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150)
            img_buffer.seek(0)
            genre_chart_url = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close()

        # 최근 영화 목록
        recent_movies = movies[:20]

        # 최근 수집일
        last_crawled = None
        if movies.exists():
            last_crawled = movies.first().crawled_at.strftime('%Y-%m-%d %H:%M')

        context = {
            'movies': recent_movies,
            'movie_count': total_movies,
            'stats': stats,
            'rating_chart_url': rating_chart_url,
            'genre_chart_url': genre_chart_url,
            'last_crawled': last_crawled,
            'genres': genre_counts,
        }

        return render(request, 'data_analysis/movie_visualization.html', context)
    except Exception as e:
        logger.error(f"Movie visualization error: {str(e)}")
        return render(request, 'data_analysis/movie_visualization.html', {'error': str(e)})

@csrf_exempt
def get_movie_data(request):
    """영화 데이터 API"""
    try:
        movies = Movie.objects.all().order_by('-crawled_at')

        # 장르별 분포
        genre_data = []
        for movie in movies:
            if movie.genre:
                genres = movie.genre.split(',')
                for genre in genres:
                    genre_data.append(genre.strip())

        genre_counts = Counter(genre_data)

        # 평점 분포
        rating_data = [movie.rating for movie in movies if movie.rating]

        # 월별 수집 데이터
        monthly_data = {}
        for movie in movies:
            month = movie.crawled_at.strftime('%Y-%m')
            monthly_data[month] = monthly_data.get(month, 0) + 1

        return JsonResponse({
            'success': True,
            'data': {
                'total_movies': movies.count(),
                'avg_rating': sum(rating_data) / len(rating_data) if rating_data else 0,
                'genres': dict(genre_counts.most_common(10)),
                'ratings': rating_data,
                'monthly': monthly_data,
                'recent_movies': [
                    {
                        'title': movie.title,
                        'rating': movie.rating,
                        'genre': movie.genre,
                        'release_date': movie.release_date.strftime('%Y-%m-%d') if movie.release_date else None,
                        'crawled_at': movie.crawled_at.strftime('%Y-%m-%d %H:%M')
                    }
                    for movie in movies[:10]
                ]
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@csrf_exempt
def crawl_movies(request):
    """영화 크롤링 실행"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            max_movies = data.get('max_movies', 50)

            # 네이버 영화 인기순위만 크롤링
            crawler_manager = MovieCrawlerManager()
            result = crawler_manager.crawl_naver_movies(max_movies)

            # 전체 영화 수 조회
            total_movies = Movie.objects.count()

            return JsonResponse({
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'total_movies': total_movies,
                'details': result.get('data', {})
            })

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': '잘못된 요청 형식입니다.'})
        except Exception as e:
            logger.error(f"크롤링 중 오류 발생: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})

@csrf_exempt
def clear_movie_data(request):
    """영화 데이터 초기화"""
    if request.method == 'POST':
        try:
            deleted_count = Movie.objects.count()
            Movie.objects.all().delete()

            return JsonResponse({
                'success': True,
                'message': f'{deleted_count}개의 영화 데이터가 삭제되었습니다.'
            })
        except Exception as e:
            logger.error(f"데이터 삭제 중 오류 발생: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})

def test_crawler(request):
    """크롤러 테스트 페이지"""
    return render(request, 'data_analysis/test_crawler.html')

@csrf_exempt
def dynamic_crawl(request):
    """동적 크롤링 실행"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            url = data.get('url')
            selectors = data.get('selectors', [])

            if not url:
                return JsonResponse({'success': False, 'message': 'URL이 필요합니다.'})

            crawler = DynamicCrawler()

            # 결과 수집
            results = []
            for selector in selectors:
                if selector.strip():
                    result = crawler.crawl_site(url, selector.strip())
                    results.extend(result)

            return JsonResponse({
                'success': True,
                'message': f'{len(results)}개의 요소를 찾았습니다.',
                'results': results[:50]  # 최대 50개만 반환
            })
        except Exception as e:
            logger.error(f"동적 크롤링 중 오류 발생: {str(e)}")
            return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})

    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})

def custom_visualization(request):
    """커스텀 사이트 데이터 시각화"""
    try:
        # 커스텀 데이터 가져오기
        custom_data = CustomData.objects.all().order_by('-crawled_at')

        # 사이트별 데이터 수 계산
        site_data_counts = {}
        for data in custom_data:
            site_name = data.site_name
            site_data_counts[site_name] = site_data_counts.get(site_name, 0) + 1

        # 시계열 데이터 생성
        daily_data = {}
        for data in custom_data:
            date = data.crawled_at.strftime('%Y-%m-%d')
            daily_data[date] = daily_data.get(date, 0) + 1

        # 차트 생성
        distribution_chart_url = None
        timeseries_chart_url = None

        if custom_data:
            # 분포 차트
            if site_data_counts:
                plt.figure(figsize=(10, 6))
                plt.bar(site_data_counts.keys(), site_data_counts.values())
                plt.title('사이트별 데이터 분포')
                plt.xlabel('사이트')
                plt.ylabel('데이터 수')
                plt.xticks(rotation=45)
                plt.tight_layout()

                img_buffer = io.BytesIO()
                plt.savefig(img_buffer, format='png')
                img_buffer.seek(0)
                distribution_chart_url = base64.b64encode(img_buffer.getvalue()).decode()
                plt.close()

            # 시계열 차트
            if daily_data:
                plt.figure(figsize=(10, 6))
                dates = sorted(daily_data.keys())
                values = [daily_data[date] for date in dates]
                plt.plot(dates, values, marker='o')
                plt.title('일별 데이터 수집 추이')
                plt.xlabel('날짜')
                plt.ylabel('데이터 수')
                plt.xticks(rotation=45)
                plt.tight_layout()

                img_buffer = io.BytesIO()
                plt.savefig(img_buffer, format='png')
                img_buffer.seek(0)
                timeseries_chart_url = base64.b64encode(img_buffer.getvalue()).decode()
                plt.close()

        # 테이블 데이터
        custom_data_table = []
        custom_data_columns = ['사이트명', '데이터 타입', '키', '값', '수집일시']

        for data in custom_data[:50]:  # 최대 50개만 표시
            custom_data_table.append([
                data.site_name,
                data.data_type,
                data.data_key,
                data.data_value[:100] + '...' if len(data.data_value) > 100 else data.data_value,
                data.crawled_at.strftime('%Y-%m-%d %H:%M')
            ])

        context = {
            'custom_data': custom_data_table,
            'custom_data_columns': custom_data_columns,
            'site_data_counts': site_data_counts,
            'data_count': custom_data.count(),
            'last_crawled': custom_data.first().crawled_at.strftime('%Y-%m-%d %H:%M') if custom_data else None,
            'distribution_chart_url': distribution_chart_url,
            'timeseries_chart_url': timeseries_chart_url,
        }

        return render(request, 'data_analysis/custom_visualization.html', context)
    except Exception as e:
        logger.error(f"커스텀 시각화 중 오류 발생: {str(e)}")
        return render(request, 'data_analysis/custom_visualization.html', {'error': str(e)})

@csrf_exempt
def crawl_custom_site(request):
    """커스텀 사이트 크롤링"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            url = data.get('url')
            max_items = data.get('max_items', 50)
            selectors = data.get('selectors', {})

            if not url:
                return JsonResponse({'success': False, 'message': 'URL이 필요합니다.'})

            crawler = DynamicCrawler()

            # 각 선택자별로 크롤링
            all_results = []
            for data_type, selector in selectors.items():
                if selector.strip():
                    results = crawler.crawl_site(url, selector.strip())

                    # 결과를 CustomData 형태로 변환
                    for i, result in enumerate(results[:max_items]):
                        try:
                            # URL에서 사이트명 추출
                            from urllib.parse import urlparse
                            parsed_url = urlparse(url)
                            site_name = parsed_url.netloc

                            # 데이터 저장
                            custom_data = CustomData.objects.create(
                                site_url=url,
                                site_name=site_name,
                                data_type=data_type,
                                data_key=f"{data_type}_{i+1}",
                                data_value=result if isinstance(result, str) else str(result)
                            )
                            all_results.append(custom_data)
                        except Exception as e:
                            logger.error(f"데이터 저장 중 오류: {str(e)}")
                            continue

            return JsonResponse({
                'success': True,
                'message': f'{len(all_results)}개의 데이터가 수집되었습니다.',
                'count': len(all_results)
            })
        except Exception as e:
            logger.error(f"커스텀 사이트 크롤링 중 오류 발생: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})

def map_visualization(request):
    """지도 시각화 페이지"""
    try:
        locations = MapLocation.objects.all().order_by('name')

        # 기본 지도 중심 좌표 (서울)
        default_lat = 37.5665
        default_lng = 126.9780

        # 지도 생성
        m = folium.Map(location=[default_lat, default_lng], zoom_start=12)

        # 위치 데이터가 있으면 마커 추가
        if locations.exists():
            # 첫 번째 위치를 지도 중심으로 설정
            first_location = locations.first()
            m = folium.Map(location=[first_location.latitude, first_location.longitude], zoom_start=12)

            # 모든 위치에 마커 추가
            for location in locations:
                popup_html = f"""
                <div style="width: 200px;">
                    <h4>{location.name}</h4>
                    <p><strong>주소:</strong> {location.address or '정보 없음'}</p>
                    <p>{location.description or ''}</p>
                </div>
                """
                folium.Marker(
                    location=[location.latitude, location.longitude],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=location.name,
                    icon=folium.Icon(color=location.marker_color)
                ).add_to(m)

        # 지도를 HTML로 변환
        map_html = m._repr_html_()

        context = {
            'locations': locations,
            'total_locations': locations.count(),
            'map_html': map_html,
        }

        return render(request, 'data_analysis/map_visualization.html', context)
    except Exception as e:
        logger.error(f"지도 시각화 중 오류 발생: {str(e)}")
        return render(request, 'data_analysis/map_visualization.html', {'error': str(e)})

@csrf_exempt
def add_map_location(request):
    """지도 위치 추가"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            location = MapLocation.objects.create(
                name=data.get('name'),
                latitude=float(data.get('latitude')),
                longitude=float(data.get('longitude')),
                address=data.get('address', ''),
                description=data.get('description', ''),
                marker_color=data.get('marker_color', 'red')
            )

            return JsonResponse({
                'success': True,
                'message': '위치가 추가되었습니다.',
                'location': {
                    'id': location.id,
                    'name': location.name,
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'address': location.address,
                    'description': location.description,
                    'marker_color': location.marker_color
                }
            })
        except Exception as e:
            logger.error(f"위치 추가 중 오류 발생: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})

@csrf_exempt
def update_map(request):
    """지도 데이터 업데이트"""
    if request.method == 'GET':
        try:
            locations = MapLocation.objects.all()

            locations_data = []
            for location in locations:
                locations_data.append({
                    'id': location.id,
                    'name': location.name,
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'address': location.address,
                    'description': location.description,
                    'marker_color': location.marker_color
                })

            return JsonResponse({
                'success': True,
                'locations': locations_data
            })
        except Exception as e:
            logger.error(f"지도 업데이트 중 오류 발생: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})

def map_html(request):
    """지도 HTML 생성 및 반환"""
    try:
        # URL 파라미터 가져오기
        lat = float(request.GET.get('lat', 37.5665))
        lng = float(request.GET.get('lng', 126.9780))
        zoom = int(request.GET.get('zoom', 12))
        map_type = request.GET.get('type', 'OpenStreetMap')
        show_markers = request.GET.get('markers', 'true').lower() == 'true'

        # 지도 타입에 따른 타일 설정
        tiles = map_type
        if map_type == 'Stamen Terrain':
            tiles = 'Stamen Terrain'
        elif map_type == 'Stamen Toner':
            tiles = 'Stamen Toner'
        elif map_type == 'CartoDB positron':
            tiles = 'CartoDB positron'

        # 지도 생성
        m = folium.Map(location=[lat, lng], zoom_start=zoom, tiles=tiles)

        # 마커 표시 여부 확인
        if show_markers:
            locations = MapLocation.objects.all()

            for location in locations:
                popup_html = f"""
                <div style="width: 200px;">
                    <h4>{location.name}</h4>
                    <p><strong>주소:</strong> {location.address or '정보 없음'}</p>
                    <p>{location.description or ''}</p>
                </div>
                """
                folium.Marker(
                    location=[location.latitude, location.longitude],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=location.name,
                    icon=folium.Icon(color=location.marker_color)
                ).add_to(m)

        # 지도를 HTML로 변환
        map_html = m._repr_html_()

        # HTML 응답 반환
        from django.http import HttpResponse
        return HttpResponse(map_html)
    except Exception as e:
        logger.error(f"지도 HTML 생성 중 오류 발생: {str(e)}")
        return HttpResponse(f"지도를 생성하는 중 오류가 발생했습니다: {str(e)}", status=500)

def wordcloud_visualization(request):
    """워드클라우드 시각화 페이지"""
    try:
        # 최근 텍스트 분석 결과 가져오기
        latest_analysis = TextAnalysis.objects.order_by('-created_at').first()

        wordcloud_image = None
        word_frequencies = []
        analysis_date = None
        original_text = ""

        if latest_analysis:
            analysis_date = latest_analysis.created_at
            original_text = latest_analysis.source_text[:200] + "..." if len(latest_analysis.source_text) > 200 else latest_analysis.source_text

            # 워드클라우드 이미지 재생성 (최신 데이터로)
            try:
                from .models import create_wordcloud_directly
                result = create_wordcloud_directly(latest_analysis.source_text)

                # JsonResponse를 dict로 변환
                if hasattr(result, 'content'):
                    import json
                    result_data = json.loads(result.content.decode('utf-8'))
                    if result_data.get('success') and result_data.get('wordcloud_image'):
                        wordcloud_image = result_data['wordcloud_image']
                else:
                    # 이미 dict인 경우
                    if result.get('success') and result.get('wordcloud_image'):
                        wordcloud_image = result['wordcloud_image']
            except Exception as e:
                print(f"워드클라우드 재생성 실패: {e}")
                # 기존 이미지 파일이 있으면 사용
                if latest_analysis.wordcloud_image:
                    wordcloud_image = latest_analysis.wordcloud_image.url

            # 단어 빈도 데이터 가져오기
            word_frequencies = WordFrequency.objects.filter(
                text_analysis=latest_analysis
            ).order_by('-count')[:20]

        context = {
            'wordcloud_image': wordcloud_image,
            'word_frequencies': word_frequencies,
            'analysis_date': analysis_date,
            'original_text': original_text,
            'total_analyses': TextAnalysis.objects.count(),
            'has_data': latest_analysis is not None,
        }

        return render(request, 'data_analysis/wordcloud_visualization.html', context)
    except Exception as e:
        logger.error(f"워드클라우드 시각화 중 오류 발생: {str(e)}")
        return render(request, 'data_analysis/wordcloud_visualization.html', {'error': str(e)})

@csrf_exempt
def analyze_text(request):
    """텍스트 분석 실행"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data.get('text', '').strip()

            if not text:
                return JsonResponse({
                    'success': False,
                    'message': '텍스트를 입력해주세요.'
                }, status=400)

            if len(text) < 10:
                return JsonResponse({
                    'success': False,
                    'message': '최소 10자 이상의 텍스트를 입력해주세요.'
                }, status=400)

            # 워드클라우드 생성 함수 호출
            result = create_wordcloud_directly(text)

            # result가 dict이므로 JsonResponse로 변환
            if result.get('success'):
                return JsonResponse(result)
            else:
                return JsonResponse(result, status=500)

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': '잘못된 요청 형식입니다.'
            }, status=400)
        except Exception as e:
            logger.error(f"텍스트 분석 중 오류 발생: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'텍스트 분석 중 오류가 발생했습니다: {str(e)}'
            }, status=500)

    return JsonResponse({
        'success': False,
        'message': '잘못된 요청 방법입니다.'
    }, status=405)
