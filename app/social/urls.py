from django.urls import path
from .views import PostListCreateAPIView, create_post, update_post, delete_post, post_detail, stream

app_name = 'social'

urlpatterns = [
    path("index/", stream, name="index"),
    path('api/posts/', PostListCreateAPIView.as_view(), name='post_list_create'),
    path('post/new/', create_post, name='create_post'),
    path('post/<int:auto_id>/update/', update_post, name='update_post'),
    path('post/<int:auto_id>/delete/', delete_post, name='delete_post'),
    path('post/<int:auto_id>/', post_detail, name='post_detail'),
]
