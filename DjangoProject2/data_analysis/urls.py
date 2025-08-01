from django.urls import path
from . import views

app_name = 'data_analysis'

urlpatterns = [
    # Dashboard with all visualizations
    path('', views.dashboard, name='dashboard'),

    # Movie data visualization
    path('movie/', views.movie_visualization, name='movie_visualization'),
    path('movie/crawl/', views.crawl_movies, name='crawl_movies'),
    path('movie/get_data/', views.get_movie_data, name='get_movie_data'),
    path('movie/clear_data/', views.clear_movie_data, name='clear_movie_data'),

    # 테스트 크롤러 페이지
    path('test_crawler/', views.test_crawler, name='test_crawler'),
    path('dynamic_crawl/', views.dynamic_crawl, name='dynamic_crawl'),

    # Custom site data visualization
    path('custom/', views.custom_visualization, name='custom_visualization'),
    path('custom/crawl/', views.crawl_custom_site, name='crawl_custom_site'),

    # Map visualization
    path('map/', views.map_visualization, name='map_visualization'),
    path('map/add_location/', views.add_map_location, name='add_map_location'),
    path('map/update/', views.update_map, name='update_map'),
    path('map_html/', views.map_html, name='map_html'),

    # Word cloud visualization
    path('wordcloud/', views.wordcloud_visualization, name='wordcloud_visualization'),
    path('wordcloud/analyze/', views.analyze_text, name='analyze_text'),
]
