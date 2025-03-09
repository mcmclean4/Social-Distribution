from django.urls import path
from . import views
from . import post_views
from . import comment_views
from . import comment_like_views
from . import like_views
from .views import *
from .inbox_views import(InboxView, inbox_view, follow_inbox_view, )
from .follow_views import (FollowerDetailView, FollowersListView, follow_view, followers_view, unfollow_view, following_view, friends_view)
from .image_views import( getImageWithSerial, getImageWithFQID)
from .github_activity import(github_authorize, github_callback)

app_name = 'social'

urlpatterns = [

    path("index/", views.stream, name="index"),
    path("login/", views.login_page, name='login'),
    path('logout/', views.logout_page, name='logout'),
    path('register/', views.register, name='register'),

    path('api/authors/', views.get_authors, name='get_authors'),
    path('profile/<int:id>', views.profile_page, name='profile_page'),
    path('profile/<int:id>/edit', views.profile_edit, name="profile_edit"),
    path('api/authors/<int:id>', views.get_author, name='get_author'),

    path('api/posts/', post_views.PostListCreateAPIView.as_view(), name='post_list_create'), # getting all the posts
    path('api/posts/<int:internal_id>/', post_views.PostDetailAPIView.as_view(), name='post_detail'),  # getting all the posts as well as updating, deleting them
    path('api/authors/<int:id>/posts/', post_views.api_get_author_and_all_post, name='api_get_author_and_all_post'),
    path('api/authors/<int:author_id>/posts/<int:internal_id>/', post_views.get_author_and_post, name='get_author_and_post'),

    # Image Posts
    path('api/authors/<int:author_serial>/posts/<int:post_serial>/image', getImageWithSerial, name='get_image_with_serial'),
    path('api/posts/<path:post_fqid>/image', getImageWithFQID, name='get_image_with_FQID'),

    path('post/', post_views.create_post, name='create_post'),
    path('post/<int:internal_id>/update/', post_views.update_post, name='update_post'),
    path('post/<int:internal_id>/delete/', post_views.delete_post, name='delete_post'),
    path('post/<int:internal_id>/', post_views.post_detail, name='post_detail'),

    # Github authorization
    path('github/authorize/', github_authorize, name='github_authorize'),
    path('github/callback/', github_callback, name='github_callback'),
    
    path("api/authors/<str:author_id>/followers", FollowersListView.as_view(), name="get_followers_a"),
    path("api/authors/<str:author_id>/followers/", FollowersListView.as_view(), name="get_followers"),
    path("api/authors/<str:author_id>/followers/<path:follower_fqid>", FollowerDetailView.as_view(), name="manage_follower"),
    path("api/authors/<str:author_id>/inbox",InboxView.as_view(), name="api_inbox"),

    ############################## Like post
    path('api/authors/<str:author_id>/posts/<str:post_id>/like/', views.PostLikeView.as_view(), name='like_post'),
    # Who liked this comment
    path('api/authors/<str:author_id>/posts/<str:post_id>/comments/<path:comment_fqid>/likes/', 
        comment_like_views.get_comment_likes, name='get_comment_likes'),

    # Like a comment (POST)
    path('api/authors/<str:author_id>/posts/<str:post_id>/comments/<path:comment_fqid>/like/', 
        comment_like_views.like_comment, name='like_comment'),

    # Things liked by author
    path('api/authors/<str:author_id>/liked/', 
        like_views.get_liked_by_author, name='get_liked_by_author'),

    # Get a single like
    path('api/authors/<str:author_id>/liked/<str:like_serial>/', 
        like_views.get_single_like, name='get_single_like'),

    # Things liked by author (by FQID)
    path('api/authors/<path:author_fqid>/liked/', 
        like_views.get_liked_by_author_fqid, name='get_liked_by_author_fqid'),

    # Get a single like by FQID
    path('api/liked/<path:like_fqid>/', 
        like_views.get_like_by_fqid, name='get_like_by_fqid'),
    
    # get likes
    path('api/authors/<str:author_id>/posts/<str:post_id>/likes/', 
        like_views.get_post_likes, name='get_post_likes'),
    # Comments
    path('api/authors/<str:author_id>/posts/<str:post_serial>/comments/', 
        comment_views.get_post_comments, name='post_comments'),  # Handles both GET and POST
    path('api/posts/<path:post_fqid>/comments/', 
        comment_views.get_comments_by_post_fqid, name='get_comments_by_post_fqid'),
    path('api/authors/<str:author_id>/posts/<str:post_serial>/comments/<path:remote_comment_fqid>/', 
        comment_views.get_specific_comment, name='get_specific_comment'),

    # Comment like  
    path('api/authors/<str:author_id>/posts/<str:post_id>/comments/<path:comment_id>/like/', 
        comment_like_views.like_comment, name='like_comment'),

    path("my_posts/", views.my_posts, name="my_posts"),
    path("inbox/", inbox_view, name="inbox"),
    path("follow/", follow_view, name="web_follow"),
    path("inbox/follow/", follow_inbox_view, name="web_inbox"),
    path("followers/", followers_view, name="web_followers"),
    path("following/", following_view, name="following"),
    path("unfollow/", unfollow_view, name="unfollow"),
    path("friends/", friends_view, name="friends"),
    # path('api')
]