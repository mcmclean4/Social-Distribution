from django.urls import path
from . import views
from .views import *
from .inbox_views import(InboxView, inbox_view, follow_inbox_view, )
from .follow_views import (FollowerDetailView, FollowersListView, follow_view, followers_view, unfollow_view, following_view, friends_view)
from .image_views import(getImage)

app_name = 'social'

urlpatterns = [

    path("index/", views.stream, name="index"),
    path("login/", views.login_page, name='login'),
    path('logout/', views.logout_page, name='logout'),
    path('register/', views.register, name='register'),

    path('api/authors', views.get_authors, name='get_authors'),
    path('api/authors/<int:id>', views.get_author, name='get_author'),

    # path('api/posts/', views.PostListCreateAPIView.as_view(), name='post_list_create'),
    path('api/posts/', views.api_create_post, name='post_create'),
    path('api/posts/<int:id>/', views.api_get_post_by_id, name='api_get_post_by_id'),
    path('api/authors/<int:id>/posts/', views.api_get_author_and_all_post, name='api_get_author_and_all_post'),
    path('api/authors/<int:author_id>/posts/<int:internal_id>/', views.get_author_and_post, name='get_author_and_post'),
    path('api/authors/<int:id>/posts/<int:internal_id>/update/', views.update_post, name='update_post'),
    path('api/authors/<int:id>/posts/<int:internal_id>/delete/', views.delete_post, name='delete_post'),

    # Image Posts
    #path('api/authors/<str:author_id>/posts/<int:internal_id>/image', image_views.___.as_view(), name='____'),
    path('api/posts/<int:internal_id>/image', getImage, name='get_image'),

    path('post/', views.create_post, name='create_post'),
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