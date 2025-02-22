from django.urls import path
from .views import PostListCreateAPIView, create_post, update_post, delete_post, post_detail, stream
from . import views
from django.urls import path, re_path 
from . import views
from .views import *

app_name = 'social'

from django.urls import path, re_path
from .views import (
    FollowersListView, FollowerDetailView, InboxView, inbox_view,
    follow_view, follow_inbox_view, followers_view, PostListCreateAPIView, create_post, update_post, delete_post, post_detail, stream
)

urlpatterns = [
    path("index/", views.stream, name="index"),
    path("login/", views.login_page, name='login'),
    path('logout/', views.logout_page, name='logout'),
    path('register/', views.register, name='register'),

    path('api/authors', views.get_authors, name='get_authors'),
    path('api/authors/<int:id>', views.get_author, name='get_author'),

    path('api/posts/', views.PostListCreateAPIView.as_view(), name='post_list_create'),
    path('api/posts/<uuid:post_id>/', views.PostDetailAPIView.as_view(), name='post_detail'),
    path('api/authors/<uuid:author_id>/posts/', views.AuthorPostListAPIView.as_view(), name='author_post_list'),

    path('post/new/', views.create_post, name='create_post'), 
    path('post/<int:internal_id>/update/', views.update_post, name='update_post'),
    path('post/<int:internal_id>/delete/', views.delete_post, name='delete_post'),
    path('post/<int:internal_id>/', views.post_detail, name='post_detail'),
    
    path("api/authors/<str:author_id>/followers", FollowersListView.as_view(), name="get_followers_a"),
    path("api/authors/<str:author_id>/followers/", FollowersListView.as_view(), name="get_followers"),
    path("api/authors/<str:author_id>/followers/<path:follower_fqid>", FollowerDetailView.as_view(), name="manage_follower"),
    path("api/authors/<str:author_id>/inbox",InboxView.as_view(), name="api_inbox"),
    

    path("inbox/", inbox_view, name="inbox"),
    path("follow/", follow_view, name="web_follow"),
    path("inbox/follow/", follow_inbox_view, name="web_inbox"),
    path("followers/", followers_view, name="web_followers"),
    path("following/", following_view, name="following"),
    path("unfollow/", unfollow_view, name="unfollow"),
    path("friends/", friends_view, name="friends"),
]