from django.urls import path
from .views import PostListCreateAPIView, create_post, update_post, delete_post, post_detail, stream
from . import views

app_name = 'social'

urlpatterns = [
    path("index/", stream, name="index"),
    path("login/", views.login_page, name='login'),
    path('logout/', views.logout_page, name='logout'),
    path('register/', views.register, name='register'),
    path('api/authors', views.get_authors, name='get_authors'),
    path('api/authors/<int:id>', views.get_author, name='get_author'),
    path('api/posts/', PostListCreateAPIView.as_view(), name='post_list_create'),
    path('post/new/', create_post, name='create_post'),
    path('post/<int:auto_id>/update/', update_post, name='update_post'),
    path('post/<int:auto_id>/delete/', delete_post, name='delete_post'),
    path('post/<int:auto_id>/', post_detail, name='post_detail'),
]
