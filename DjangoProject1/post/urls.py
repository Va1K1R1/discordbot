from django.urls import path
from . import views

app_name = "post"
urlpatterns = [
    path("create/", views.create_post, name="create_post"),
    path("detail/<int:post_id>/", views.get_post, name="detail_post"),
    path("list/", views.get_post_list, name="list_post"),
    path("update/<int:post_id>/", views.update_post, name="update_post"),
    path("delete/<int:post_id>/", views.delete_post, name="delete_post"),
]
