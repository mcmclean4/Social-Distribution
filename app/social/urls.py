from django.urls import path, re_path
from . import views
from . import post_views
from . import comment_views
from . import comment_like_views
from . import like_views
from . import video_views
from .views import *
from .inbox_views import(InboxView, inbox_view, follow_inbox_view, )
from .follow_views import (FollowerDetailView, FollowersListView, follow_view, followers_view, unfollow_view, following_view, friends_view, send_follow_decision_to_inbox, fetch_remote_authors_view,local_follow_finalize,send_unfollow_to_inbox)
from .image_views import( get_image_with_serial, get_image_with_fqid)
from .github_activity import(github_authorize, github_callback)
from .node_views import NodeListCreateAPIView, NodeRetrieveUpdateDestroyAPIView
from .comment_views import(get_post_comments,get_comments_by_post_fqid, get_specific_comment,send_comment_to_inbox_view, create_local_comment)
from .comment_like_views import(get_comment_likes,like_comment,send_comment_like_to_inbox)
from .like_views import(send_like_to_inbox)
from . import notifications_views

app_name = 'social'

urlpatterns = [

    #ADMIN
    path("send-command/", views.send_command, name="send_command"),
    path("start-terminal/", views.start_terminal, name="start_terminal"),
    
    path("index/", views.stream, name="index"),
    path("login/", views.login_page, name='login'),
    path('logout/', views.logout_page, name='logout'),
    path('register/', views.register, name='register'),

    # NODES
    path('api/nodes/', NodeListCreateAPIView.as_view(), name='node_list_create'),
    path('api/nodes/<int:pk>/', NodeRetrieveUpdateDestroyAPIView.as_view(), name='node_detail'),

    path('api/authors/', views.get_authors, name='get_authors'),
    path('profile/<int:id>', views.profile_page, name='profile_page'),
    path('profile/<int:id>/edit', views.profile_edit, name="profile_edit"),
    path('api/authors/<int:id>', views.get_author, name='get_author'),

    # Image Posts
    path('api/authors/<int:author_serial>/posts/<int:post_serial>/image', get_image_with_serial, name='get_image_with_serial'),
    re_path(r'^api/posts/(?P<post_fqid>.+)/image$', get_image_with_fqid, name='get_image_with_FQID'),   # Use a regex pattern to explicitly match the URL without the "/image" suffix

    path('api/posts/', post_views.PostListCreateAPIView.as_view(), name='post_list_create'), # getting all the posts
    path('api/posts/<int:internal_id>/', post_views.PostDetailAPIView.as_view(), name='post_detail'),  # getting all the posts as well as updating, deleting them
    path('api/authors/<int:id>/posts', post_views.api_get_author_and_all_post, name='api_get_author_and_all_post'),
    path('api/authors/<int:author_id>/posts/<int:internal_id>/', post_views.get_author_and_post, name='get_author_and_post'),
    

    path('post/', post_views.create_post, name='create_post'),
    path('post/<int:internal_id>/update/', post_views.update_post, name='update_post'),
    path('post/<int:internal_id>/delete/', post_views.delete_post, name='delete_post'),
    path('post/<int:internal_id>/', post_views.post_detail, name='post_detail'),

    # Video post
    path('post/video/', post_views.create_video_post, name='create_video_post'),


    path('api/authors/<int:author_serial>/posts/<int:post_serial>/video', video_views.get_video_with_serial, name='get_video_with_serial'),
    re_path(r'^social/api/posts/(.+)$', video_views.get_video_with_fqid_fix, name='get_video_with_fqid_fix'),

    path('debug/url/<int:post_id>/', video_views.debug_image_url, name='debug_image_url'),
    path('debug/current-url/', video_views.debug_video_url, name='debug_video_url'),

    path('test-video/<int:post_id>/', video_views.test_video, name='test_video'),
    # Github authorization
    path('github/authorize/', github_authorize, name='github_authorize'),
    path('github/callback/', github_callback, name='github_callback'),
    
    path("api/authors/<str:author_id>/followers", FollowersListView.as_view(), name="get_followers_a"),
    path("api/authors/<str:author_id>/followers/", FollowersListView.as_view(), name="get_followers"),
    path("api/authors/<str:author_id>/followers/<path:follower_fqid>", FollowerDetailView.as_view(), name="manage_follower"),
    path("api/authors/<str:author_id>/inbox",InboxView.as_view(), name="api_inbox"),
    path("api/authors/<str:author_id>/inbox/",InboxView.as_view(), name="api_inbox"),

    ############################## Like post
    path('api/authors/<str:author_id>/posts/<str:post_id>/like/', views.PostLikeView.as_view(), name='like_post'),
    # Who liked this comment
    path('api/authors/<str:author_id>/posts/<str:post_serial>/comments/<path:comment_fqid>/likes/', 
        comment_like_views.get_comment_likes, name='get_comment_likes'),

    # Like a comment (POST)
    path('api/authors/<str:author_id>/posts/<str:post_id>/comments/<path:comment_fqid>/like/', 
        comment_like_views.like_comment, name='like_comment'),

    # Things liked by author
    path('api/authors/<str:author_id>/liked', 
        like_views.get_liked_by_author, name='get_liked_by_author'),

    # Get a single like
    path('api/authors/<str:author_id>/liked/<str:like_serial>/', 
        like_views.get_single_like, name='get_single_like'),

    # Things liked by author (by FQID)
    path('api/authors/<path:author_fqid>/liked/', 
        like_views.get_liked_by_author_fqid, name='get_liked_by_author_fqid'),

    path('api/posts/<path:post_fqid>/liked/', 
        like_views.get_liked_by_post_fqid, name='get_liked_by_post_fqid'),

    # Get a single like by FQID
    path('api/liked/<path:like_fqid>/', 
        like_views.get_like_by_fqid, name='get_like_by_fqid'),
    
    # likes API
    path('api/authors/<str:author_id>/posts/<str:post_id>/likes/', 
        like_views.get_post_likes, name='get_post_likes'),

    path('api/posts/<path:post_fqid>/likes', 
        like_views.get_post_likes_by_fqid, name='get_post_likes_fqid'),

    # Comments API
    path('api/authors/<str:author_id>/posts/<str:post_serial>/comments/', 
        comment_views.get_post_comments, name='post_comments'),  # Handles both GET and POST
    path('api/posts/<path:post_fqid>/comments/', 
        comment_views.get_comments_by_post_fqid, name='get_comments_by_post_fqid'),
    path('api/authors/<str:author_id>/posts/<str:post_serial>/comments/<path:remote_comment_fqid>/', 
        comment_views.get_specific_comment, name='get_specific_comment'),

    # Comment like  
    path('api/authors/<str:author_id>/posts/<str:post_id>/comments/<path:comment_id>/like/', 
        comment_like_views.like_comment, name='like_comment'),

    # Commented API
    path('api/authors/<str:author_id>/commented',  # works
        comment_views.get_author_comments, name='get_author_comments'),
    path('api/authors/<path:author_fqid>/commented/', # works 
        comment_views.get_author_comments_by_fqid, name='get_author_comments_by_fqid'),
    path('api/authors/<str:author_id>/commented/<str:comment_serial>/', # works
        comment_views.get_specific_comment_by_serial, name='get_specific_comment_by_serial'),
    path('api/commented/<path:comment_fqid>/', # works
        comment_views.get_comment_by_fqid, name='get_comment_by_fqid'),


    path("my_posts/", views.my_posts, name="my_posts"),
    path("inbox/", inbox_view, name="inbox"),
    path("follow/", follow_view, name="web_follow"),
    path("inbox/follow/", follow_inbox_view, name="web_inbox"),
    path("followers/", followers_view, name="web_followers"),
    path("following/", following_view, name="following"),
    path("unfollow/", unfollow_view, name="unfollow"),
    path("friends/", friends_view, name="friends"),
    path("remote-authors/", fetch_remote_authors_view, name="fetch_remote_authors"),
    path("api/follow/confirm/", local_follow_finalize, name="local_follow_finalize"),
    path('api/create-local-comment/', create_local_comment, name='create_local_comment'),


    # path('api')

    path('api/posts/<path:post_fqid>', post_views.get_post_with_fqid, name='post_detail_with_fqid'),    # must come after other urls that start with 'api/posts/'
    re_path(r'^api/authors/(?P<author_fqid>.+)$', views.get_author_with_fqid, name='get_author_with_fqid'), # needs to be after the get_author_and_post line
    path('api/send-comment-to-inbox/', send_comment_to_inbox_view, name='send_comment_to_inbox'),
    path('api/send-like-to-inbox/', send_like_to_inbox, name='send_like_to_inbox'),

    path('api/send-comment-like-to-inbox/', send_comment_like_to_inbox, name='send_comment_like_to_inbox'),
    path('api/send-follow-decision-to-inbox/', send_follow_decision_to_inbox, name='send_follow_decision_to_inbox'),
    path('api/send-unfollow-to-inbox/', send_unfollow_to_inbox, name='send_unfollow_to_inbox'),

    path('notifications/', notifications_views.notifications_home, name='notifications_home'),
    path('notifications/likes/', notifications_views.notifications_likes, name='notifications_likes'),
    path('notifications/comments/', notifications_views.notifications_comments, name='notifications_comments'),
    path('notifications/mark-read/<int:notification_id>/', notifications_views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', notifications_views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/count/', notifications_views.get_notification_count, name='notification_count'),

]