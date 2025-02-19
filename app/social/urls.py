from django.urls import path
from .views import PostListCreateAPIView, create_post, update_post, delete_post, post_detail, stream
from . import views
from django.urls import path, re_path 
from . import views

app_name = 'social'

from django.urls import path, re_path
from .views import (
    FollowersView, FollowerDetailView, InboxView, FollowRequestView,
    follow_view, follow_inbox_view, followers_view, PostListCreateAPIView, create_post, update_post, delete_post, post_detail, stream
)

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
    # ✅ API Endpoints (Use `api_` prefix to prevent conflicts)
    re_path(r"^api/authors/(?P<author_id>.+)/followers/?$", FollowersView.as_view(), name="api_followers"),
    path("api/authors/<path:author_id>/followers/<path:foreign_author_fqid>/", FollowerDetailView.as_view(), name="api_follower_detail"),
    re_path(r"^api/authors/(?P<author_id>.+)/inbox/?$", InboxView.as_view(), name="api_inbox"),  # ✅ Accepts both /inbox and /inbox/
    path("api/authors/<path:author_id>/follow/", FollowRequestView.as_view(), name="api_follow_request"),

    

    # ✅ Frontend Pages (Use `web_` prefix for clarity)
    path("follow/", follow_view, name="web_follow"),
    path("inbox/follow/", follow_inbox_view, name="web_inbox"),
    path("followers/", followers_view, name="web_followers"),
]
