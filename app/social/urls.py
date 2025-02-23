from django.urls import path
from . import views
from .views import *
from .inbox_views import(InboxView, inbox_view, follow_inbox_view, )
from .follow_views import (FollowerDetailView, FollowersListView, follow_view, followers_view, unfollow_view, following_view, friends_view)

app_name = 'social'

urlpatterns = [

    path("index/", views.stream, name="index"),
    path("login/", views.login_page, name='login'),
    path('logout/', views.logout_page, name='logout'),
    path('register/', views.register, name='register'),

    path('api/authors', views.get_authors, name='get_authors'),
    path('profile/<int:id>', views.profile_page, name='profile_page'),
    path('profile/<int:id>/edit', views.profile_edit, name="profile_edit"),
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