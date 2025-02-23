from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView 
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from .serializers import PostSerializer, AuthorSerializer
from .models import Post, Author, Follow, FollowRequest,Inbox
import requests
from django.shortcuts import render, redirect, get_object_or_404
from .forms import PostForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.views import View
from django.views.generic import ListView
from django.contrib import messages
from urllib.parse import unquote
from django.db import transaction  # Correct placement of transaction import
from django.utils import timezone

# Like
from .models import Post, PostLike, Comment
from .serializers import PostLikeSerializer


import requests  # Correct placement of requests import
from django.conf import settings
import json
from rest_framework.pagination import PageNumberPagination


######################################
#           STREAM/INDEX AREA        
######################################

@login_required
def stream(request):
    # Get user's friends
    # user_friends = request.user.author.friends.all()

    # Filter posts based on visibility
    post_list = Post.objects.annotate(
        like_count=Count('likes')
    ).filter(
        (Q(visibility='PUBLIC'))  # Show public posts
        #  Q(visibility='FRIENDS', author__in=user_friends))  # Show friends' posts || currently
        & ~Q(visibility='DELETED')  # Exclude deleted posts
        & ~Q(visibility='UNLISTED')  # Exclude unlisted posts
    ).order_by('-published')

    # Handle likes for comments
    for post in post_list:
        for comment in post.comments.all():
            comment.is_liked = request.user.author in comment.likes.all() if request.user.is_authenticated else False

    # Pagination
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)

    return render(request, 'social/index.html', {'posts': posts})


######################################
#           AUTHOR AREA             
######################################


def login_page(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not User.objects.filter(username=username).exists():
            messages.error(request, 'Username does not exist')
            return redirect('social:login')

        user = authenticate(username=username, password=password)

        if user is None:
            messages.error(request, 'Password does not match username')
            return redirect('social:login')

        else:
            login(request, user)
            return redirect('social:index')

    return render(request, 'social/login.html')


def logout_page(request):
    logout(request)
    return redirect('social:login')


def register(request):
    if request.method == "POST":
        print(request.POST)
        username = request.POST.get('username')
        password = request.POST.get('password')
        displayName = request.POST.get('displayName')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            # return 400 since new user is not created
            return render(request, 'social/register.html', status=400)

        user = User.objects.create_user(username=username, password=password)

        host = "http://localhost:8000/social/api/"

        author = Author.objects.create(
            user=user, host=host, displayName=displayName)

        author.save()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('social:index')

        # create_author()

    return render(request, 'social/register.html')

@api_view(['GET'])
def get_author(request, id):

    author = Author.objects.get(
        id=f"http://localhost:8000/social/api/authors/{id}")
    serializer = AuthorSerializer(author)
    return Response(serializer.data)

@api_view(['GET'])
def get_authors(request):
    authors = Author.objects.all()
    serializer = AuthorSerializer(authors, many=True)
    return Response(serializer.data)


class AuthorPostListAPIView(generics.ListAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        author_id = self.kwargs['author_id']
        return Post.objects.filter(author__id=author_id)
    
class AuthorPostCreateAPIView(generics.CreateAPIView):
    serializer_class = PostSerializer

    def perform_create(self, serializer):
        author = Author.objects.get(id=self.kwargs['author_id'])
        serializer.save(author=author)


######################################
#            POST AREA              
######################################

class PostListCreateAPIView(generics.ListCreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user.author)

class PostDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    lookup_field = 'internal_id'

    def get_object(self):
        return Post.objects.get(internal_id=self.kwargs['internal_id'])
    
    def perform_create(self, serializer):
        author = Author.objects.get(id=self.kwargs['author_id'])
        serializer.save(author=author)


class PostDeleteAPIView(generics.DestroyAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    lookup_field = 'internal_id'

    def get_object(self):
        return Post.objects.get(internal_id=self.kwargs['internal_id'])
    
    def perform_destroy(self, instance):
        # Soft delete instead of permanent delete
        instance.visibility = 'DELETED'
        instance.save()

@login_required
def my_posts(request):
    try:
        user = Author.objects.get(user=request.user)
    except Author.DoesNotExist:
        print("No author found")
        return redirect('social:index')

    post_list = Post.objects.filtered(
        filter_type='author',
        author=user,
        visibilities='ALL'
    )
    print(post_list)

    # Pagination
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)

    return render(request, 'social/my_posts.html', {'my_posts': posts})

@login_required
def create_post(request):
    try:
        # First check if Author exists for the user
        try:
            author = Author.objects.get(user=request.user)
        except Author.DoesNotExist:
            # Create new Author if doesn't exist
            author = Author.objects.create(
                user=request.user,
                type='author',
                displayName=request.user.username,
            )
            author.save()
        
        if request.method == "POST":
            form = PostForm(request.POST, request.FILES)
            if form.is_valid():
                post = form.save(commit=False)
                post.author = author
                
                # Generate a unique URL-based ID if not already set
                if not post.id:
                    post.id = f"http://localhost:8000/social/api/authors/{author.id}/posts/{post.internal_id}"
                
                post.save()
                return redirect('social:index')
    except Exception as e:
        print(f"Error creating post: {str(e)}")  # For debugging
        messages.error(request, "Error creating post. Please try again.")
    
    form = PostForm()
    return render(request, 'social/create_post.html', {'form': form})

@api_view(['POST'])
def api_create_post(request):
    if request.method == 'POST':
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)  # You can adjust this if you want to assign authors differently
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@login_required
def delete_post(request, internal_id):
    try:
        # First try to get the post without author check
        post = Post.objects.get(internal_id=internal_id)
        
        # Print debug information
        print(f"Post ID: {internal_id}")
        print(f"Post Author: {post.author.user}")
        print(f"Current User: {request.user}")
        
        # Then check if user is author
        if post.author.user != request.user:
            print("User is not the author")
            return redirect('social:index')
            
        if request.method == "POST":
            post.visibility = 'DELETED'
            post.save()
            # print(f"Post {internal_id} marked as deleted") 
            return redirect('social:index')
            
    except Post.DoesNotExist:
        print(f"No post found with ID: {internal_id}")
        
    return redirect('social:index')

@login_required
def update_post(request, internal_id):
    post = get_object_or_404(Post, internal_id=internal_id, author__user=request.user)

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('social:index')

    else:
        form = PostForm(instance=post)

    return render(request, 'social/update_post.html', {'form': form})

def post_detail(request, internal_id):
    post = get_object_or_404(Post, internal_id=internal_id)
    return render(request, 'social/post_detail.html', {'post': post})

@api_view(['PUT'])
def api_update_post(request, internal_id):
    try:
        post = Post.objects.get(internal_id=internal_id)
    except Post.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = PostSerializer(post, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def api_delete_post(request, internal_id):
    try:
        post = Post.objects.get(internal_id=internal_id)
    except Post.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    
    post.delete()
    return Response({"detail": "Post deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
def api_get_author_and_all_post(request, id):
    try:
        author = Author.objects.get(id=f"http://localhost:8000/social/api/authors/{id}")
    except Author.DoesNotExist:
        return Response({'error': 'Author not found'}, status=status.HTTP_404_NOT_FOUND)
    
    posts = Post.objects.filter(author=author)
    post_serializer = PostSerializer(posts, many=True)

    author_serializer = AuthorSerializer(author)

    return Response({
        'author': author_serializer.data,
        'posts': post_serializer.data
    })

# @api_view(['GET'])
# def get_author_and_post(request, author_id, internal_id):
#     try:
#         # Get the author by id
#         author = Author.objects.get(id=f"http://localhost:8000/social/api/authors/{author_id}")
        
#         # Get the post by internal_id and make sure it's linked to the correct author
#         post = Post.objects.get(internal_id=internal_id, author=author)
#     except Author.DoesNotExist:
#         return Response({'error': 'Author not found'}, status=status.HTTP_404_NOT_FOUND)
#     except Post.DoesNotExist:
#         return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

#     author_serializer = AuthorSerializer(author)
#     post_serializer = PostSerializer(post)
    
#     return Response({
#         'author': author_serializer.data,
#         'post': post_serializer.data
#     })

@api_view(['GET'])
def get_author_and_post(request, author_id, internal_id):
    try:
        # Get the author by id
        author = Author.objects.get(id=f"http://localhost:8000/social/api/authors/{author_id}")
        
        # Get the post by internal_id and make sure it's linked to the correct author
        post = Post.objects.get(internal_id=internal_id, author=author)
    except Author.DoesNotExist:
        return Response({'error': 'Author not found'}, status=status.HTTP_404_NOT_FOUND)
    except Post.DoesNotExist:
        return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

    post_serializer = PostSerializer(post)

    response_data = {
        'post': post_serializer.data
    }

    return Response(response_data)


@api_view(['GET'])
def api_get_post_by_id(request, id):
    try:
        # Construct the full URL for the post
        post_url = f"http://localhost:8000/social/api/authors/2/posts/{id}"
        
        print(f"Attempting to fetch post with URL: {post_url}")
        
        post = Post.objects.get(id=post_url)
        print(f"Post found: {post}")
    except Post.DoesNotExist:
        print(f"Post with ID {id} not found.")
        return Response({'error': 'Post not found'}, status=404)

    post_serializer = PostSerializer(post)

    print(f"Serialized Post Data: {post_serializer.data}")

    return Response(post_serializer.data)


######################################
#           FOLLOW/FOLLOWEE AREA      
######################################

def follow_view(request):
    """Shows a list of authors to follow, excluding those with pending requests"""

    if not hasattr(request.user, 'author'):
        return redirect('social:register')  # Redirect if the user has no author profile

    my_author = request.user.author  # Get the logged-in author's profile

    # Get all authors the user has already sent a follow request to
    requested_authors = FollowRequest.objects.filter(
        follower_id=my_author.id
    ).values_list('followee__id', flat=True)  # Extract followee IDs

    # Exclude the logged-in user and authors with pending requests
    authors = Author.objects.exclude(id=my_author.id).exclude(id__in=requested_authors)

    # Print final authors list
    print(f"✅ Available Authors to Follow: {[author.displayName for author in authors]}")

    return render(request, 'social/follow.html', {
        'authors': authors,
        'my_author': my_author,  # Pass full author object to template
    })

def follow_inbox_view(request):
    """Fetches the inbox and filters only follow requests."""
    
    if not hasattr(request.user, 'author'):
        return redirect('social:register')  # Redirect if the user has no author profile

    my_author = request.user.author  # Get the logged-in author's profile
    my_author_id = my_author.id
    print(f"🔍 Logged-in Author ID: {my_author_id}")  # Debugging: See Author ID in logs

    # Construct the API URL for retrieving inbox data
    inbox_url = f"{my_author_id}/inbox"

    try:
        response = requests.get(inbox_url, headers={"Content-Type": "application/json"})
        response.raise_for_status()  # Ensure non-200 responses raise an error
        inbox_data = response.json()

        # Extract only "follow" requests that are still pending
        follow_requests = [
            item for item in inbox_data.get("items", [])
            if item.get("type", "").lower() == "follow"
        ]

    except requests.exceptions.RequestException as e:  # Correct exception handling
        print(f"❌ Error fetching inbox data: {e}")
        follow_requests = []

    return render(request, "social/followInbox.html", {
        "my_author_id": my_author_id,
        "follow_requests": follow_requests  # Only follow requests are passed to the template
    })



def followers_view(request):
    """Shows the list of followers of the logged-in user with a delete option."""
    
    if not hasattr(request.user, 'author'):
        return redirect('social:register')  # Redirect if no author profile

    my_author = request.user.author  # Get logged-in author's profile
    my_author_id = my_author.id  # Get the full author ID

    # Construct the API URL to get followers
    followers_url = f"{my_author_id}/followers/"

    print(f"🔍 Fetching followers for: {my_author_id}")
    print(f"📤 Requesting: {followers_url}")

    try:
        response = requests.get(followers_url, headers={"Content-Type": "application/json"})
        
        print(f"📥 Raw Response Status: {response.status_code}")
        print(f"📥 Raw Response Headers: {response.headers}")

        response.raise_for_status()  # Ensure it raises an error if there's an issue
        
        followers_data = response.json()

        print(f"📥 Full API Response JSON: {json.dumps(followers_data, indent=4)}")  # Pretty-print the response

        followers = followers_data.get("items", [])  # Extract list of followers
        print(f"Extracted Followers: {followers}")

    except requests.exceptions.RequestException as e:
        print(f" Error fetching followers: {e}")
        followers = []

    return render(request, "social/followers.html", {
        "my_author_id": my_author_id,
        "followers": followers,
    })


def following_view(request):
    """Shows a list of authors that the logged-in user is following with an unfollow option."""

    if not hasattr(request.user, 'author'):
        return redirect('social:register')  # Redirect if no author profile

    my_author = request.user.author  # ✅ Get logged-in author's profile
    my_author_id = my_author.id  # ✅ Full author ID

    # ✅ Find authors the user is following from the `Follow` table
    following_entries = Follow.objects.filter(follower_id=my_author_id)

    following_authors = []
    for follow in following_entries:
        try:
            response = requests.get(follow.followee.id, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            author_data = response.json()
            following_authors.append(author_data)
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching author {follow.followee.id}: {e}")

    return render(request, "social/following.html", {
        "my_author_id": my_author_id,
        "following_authors": following_authors,  # ✅ List of followed authors
    })

@csrf_exempt
def unfollow_view(request):
    """Handles unfollowing an author by deleting the follow object in the database."""

    if request.method != "DELETE":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    if not hasattr(request.user, 'author'):
        return JsonResponse({"error": "User is not an author"}, status=403)

    try:
        data = json.loads(request.body)
        followee_id = data.get("followee_id")  # Get followee ID from request body
        if not followee_id:
            return JsonResponse({"error": "Missing followee ID"}, status=400)

        my_author = request.user.author  # Get logged-in author's profile

        # Delete the follow object
        deleted, _ = Follow.objects.filter(follower_id=my_author.id, followee__id=followee_id).delete()

        if deleted:
            return JsonResponse({"message": "Unfollowed successfully"}, status=200)
        else:
            return JsonResponse({"error": "Not following this author"}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)


def friends_view(request):
    """Shows a list of friends (mutual followers) of the logged-in user"""

    # ✅ Get logged-in user
    if not hasattr(request.user, 'author'):
        return redirect('social:register')  # Redirect to register if no author profile

    my_author = request.user.author
    my_author_id = my_author.id

    print(f"📌 Checking friends for: {my_author.displayName} ({my_author_id})")

    # Get people I follow
    following_ids = set(Follow.objects.filter(follower_id=my_author_id).values_list("followee_id", flat=True))

    #  Get people who follow me
    followers_ids = set(Follow.objects.filter(followee_id=my_author_id).values_list("follower_id", flat=True))

    #  Find mutual followers (friends)
    friends_ids = following_ids.intersection(followers_ids)

    #  Fetch full author details for friends
    friends = []
    for friend_id in friends_ids:
        try:
            response = requests.get(friend_id, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            friend_data = response.json()
            friends.append(friend_data)
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching friend details for {friend_id}: {e}")

    print(f"✅ Found {len(friends)} friends")

    # ✅ Render `friends.html` and pass the friends list
    return render(request, "social/friends.html", {
        "my_author": my_author,
        "friends": friends
    })


class InboxView(APIView):
    """Handles fetching and storing items in an author's inbox."""

    permission_classes = [AllowAny]

    def get(self, request, author_id):
        """
        Fetches all items (posts, likes, comments, follow requests) in the inbox.
        """
        author_id = unquote(author_id)
        expected_author_id = f"{settings.HOST}api/authors/{author_id}"

        print(f"📥 Fetching inbox for: {expected_author_id}")

        # Get the author's inbox
        author = get_object_or_404(Author, id=expected_author_id)
        inbox = Inbox.objects.filter(author=author).first()

        if not inbox:
            return Response({"type": "inbox", "items": []}, status=status.HTTP_200_OK)

        # Fetch and format items
        inbox_items = []

        # Fetch and format follow requests
        for fr in inbox.inbox_follows.all():
            follower_data = self.get_author_details(fr.follower_id)
            followee_data = self.get_author_details(fr.followee.id)

            if follower_data and followee_data:
                inbox_items.append({
                    "type": "Follow",
                    "summary": f"{follower_data['displayName']} wants to follow {followee_data['displayName']}",
                    "actor": follower_data,
                    "object": followee_data
                })

        # Fetch and format posts
        for post in inbox.inbox_posts.all():
            post_data = self.get_post_details(post.id)
            if post_data:
                inbox_items.append(post_data)

        # Fetch and format likes
        for like in inbox.inbox_likes.all():
            like_data = self.get_like_details(like.id)
            if like_data:
                inbox_items.append(like_data)

        # Fetch and format comments
        for comment in inbox.inbox_comments.all():
            comment_data = self.get_comment_details(comment.id)
            if comment_data:
                inbox_items.append(comment_data)

        print(f"📤 Returning {len(inbox_items)} items in the inbox.")
        return Response({"type": "inbox", "items": inbox_items}, status=status.HTTP_200_OK)

    def get_author_details(self, author_url):
        """Fetches author details from an API."""
        try:
            response = requests.get(author_url, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            author_data = response.json()

            return {
                "type": "author",
                "id": author_data.get("id", author_url),
                "host": author_data.get("host", author_url.split("/authors/")[0] + "/"),
                "displayName": author_data.get("displayName", "Unknown"),
                "github": author_data.get("github", ""),
                "profileImage": author_data.get("profileImage", ""),
                "page": author_data.get("page", author_url.replace("/api/", "/")),
            }
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching author details for {author_url}: {e}")
            return None

    def get_post_details(self, post_url):
        """Fetches post details from an API."""
        try:
            response = requests.get(post_url, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching post details for {post_url}: {e}")
            return None

    def get_like_details(self, like_url):
        """Fetches like details from an API."""
        try:
            response = requests.get(like_url, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching like details for {like_url}: {e}")
            return None

    def get_comment_details(self, comment_url):
        """Fetches comment details from an API."""
        try:
            response = requests.get(comment_url, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching comment details for {comment_url}: {e}")
            return None

    def post(self, request, author_id):
        """Stores any incoming request (posts, likes, comments, follows) in the inbox."""

        author_id = unquote(author_id)
        expected_author_id = f"{settings.HOST}api/authors/{author_id}"

        print(f"📥 Receiving new inbox item for: {expected_author_id}")

        author = get_object_or_404(Author, id=expected_author_id)
        inbox, created = Inbox.objects.get_or_create(author=author)

        data = request.data
        item_type = data.get("type")

        if item_type == "Follow":
            follow_request, _ = FollowRequest.objects.get_or_create(
                followee=author,
                follower_id=data["actor"]["id"],
                defaults={"summary": data.get("summary", ""), "status": "pending"}
            )
            inbox.inbox_follows.add(follow_request)

        elif item_type == "Like":
            like, _ = Like.objects.get_or_create(id=data["id"], defaults=data)
            inbox.inbox_likes.add(like)

        elif item_type == "Comment":
            comment, _ = Comment.objects.get_or_create(id=data["id"], defaults=data)
            inbox.inbox_comments.add(comment)

        elif item_type == "Post":
            post, _ = Post.objects.get_or_create(id=data["id"], defaults=data)
            inbox.inbox_posts.add(post)

        else:
            return Response({"error": "Invalid type"}, status=status.HTTP_400_BAD_REQUEST)

        inbox.save()
        print(f"✅ Stored {item_type} in inbox.")
        return Response({"message": f"{item_type} received and stored"}, status=status.HTTP_201_CREATED)




    def delete(self, request, author_id):
        """
        Denies a follow request by extracting the follower ID from the request body,
        updates the FollowRequest status to "denied," and removes it from the Inbox only.
        """
        author_id = unquote(author_id)
        expected_author_id = f"{settings.HOST}api/authors/{author_id}"
        author = get_object_or_404(Author, id=expected_author_id)

        try:
            data = request.data  # Extract body from DELETE request
            foreign_author_fqid = data.get("follower_id")

            if not foreign_author_fqid:
                return Response({"error": "Missing follower ID in request body"}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                # Find the follow request and update its status
                follow_request = FollowRequest.objects.filter(
                    follower_id=foreign_author_fqid,
                    followee=author,
                    status="pending"
                ).first()

                if follow_request:
                    follow_request.status = "denied"  # ✅ Keep it in FollowRequest, just update status
                    follow_request.save()

                    # Remove from Inbox but keep in FollowRequest
                    Inbox.objects.filter(inbox_follows=follow_request).delete()

                    print(f"❌ Denied follow request and removed from inbox: {foreign_author_fqid}")
                    return Response({"message": "Follow request denied and removed from inbox"}, status=status.HTTP_200_OK)

                return Response({"error": "Follow request not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": f"Failed to process request: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class PostLikeView(APIView):
    def get(self, request, author_id, post_id):
        """Check if the current user has liked the post"""
        try:
            # Construct the full post ID
            full_post_id = f"http://localhost:8000/posts/{post_id}"
            print(f"Looking for post with ID: {full_post_id}")
            
            post = get_object_or_404(Post, id=full_post_id)
            print(f"Found post: {post.title}")
            
            has_liked = PostLike.objects.filter(
                post=post,
                author=request.user.author
            ).exists()
            
            return Response({"has_liked": has_liked})
            
        except Post.DoesNotExist:
            return Response(
                {"error": f"Post not found with ID: {full_post_id}"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    def delete(self, request, author_id, post_id):
        """Remove a like from the post"""
        post = get_object_or_404(Post, id=f"http://localhost:8000/posts/{post_id}")
        like = PostLike.objects.filter(
            post=post,
            author=request.user.author
        )
        
        if like.exists():
            like.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        return Response(
            {"message": "Like not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    def post(self, request, author_id, post_id):
        try:
            # Debug prints
            # print("\n--- Post Like Debugging ---")
            # print(f"Request User: {request.user.username}")
            # print(f"Raw Author ID: {author_id}")
            # print(f"Raw Post ID: {post_id}")
            
            # Normalize author_id (remove URL if present)
            if isinstance(author_id, str) and '/authors/' in author_id:
                author_id = author_id.split('/authors/')[-1].split('/')[0]
            
            # Construct the full post URL
            full_post_url = f"http://localhost:8000/social/api/authors/{author_id}/posts/{post_id}"
            print(f"Constructed Post URL: {full_post_url}")
            
            # Find the post
            try:
                # Try to find the post by its full URL ID first
                post = Post.objects.get(id=full_post_url)
            except Post.DoesNotExist:
                # Fallback to finding by internal_id
                try:
                    post = Post.objects.get(internal_id=post_id)
                except Post.DoesNotExist:
                    # Log all existing posts for debugging
                    all_posts = Post.objects.all()
                    print("All Posts in Database:")
                    for p in all_posts:
                        print(f"Full ID: {p.id}")
                        print(f"Internal ID: {p.internal_id}")
                        print(f"Author ID: {p.author.id}")
                        print(f"Title: {p.title}")
                        print("---")
                    
                    return Response({
                        'error': 'Post not found', 
                        'details': {
                            'full_url': full_post_url,
                            'author_id': author_id,
                            'post_id': post_id
                        }
                    }, status=status.HTTP_404_NOT_FOUND)
            
            # Get or create the author profile for the current user
            try:
                request_user_author = request.user.author
            except Author.DoesNotExist:
                request_user_author = Author.objects.create(
                    user=request.user,
                    type='author',
                    displayName=request.user.username,
                )
            
            # Check if like already exists
            post_like, created = PostLike.objects.get_or_create(
                post=post,
                author=request_user_author
            )
            
            if not created:
                # Unlike if already liked
                post_like.delete()
                action = 'unliked'
            else:
                action = 'liked'
            
            return Response({
                'action': action,
                'like_count': post.likes.count()
            })
        
        except Exception as e:
            # Log the full exception for server-side debugging
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'An unexpected error occurred',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# comments
@api_view(['POST'])
def add_comment(request, author_id, post_id):
    try:
        # Debug prints
        print("\n--- Add Comment Debugging ---")
        print(f"Request User: {request.user.username}")
        print(f"Raw Author ID: {author_id}")
        print(f"Raw Post ID: {post_id}")
        
        # Normalize author_id (remove URL if present)
        if isinstance(author_id, str) and '/authors/' in author_id:
            author_id = author_id.split('/authors/')[-1].split('/')[0]
        
        # Construct the full post URL
        full_post_url = f"http://localhost:8000/social/api/authors/{author_id}/posts/{post_id}"
        
        # Parse comment content
        content = request.data.get('content', '').strip()
        
        # Validate comment content
        if not content:
            return Response({
                'error': 'Comment content cannot be empty'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find the post
        try:
            # Try to find the post by its full URL ID first
            post = Post.objects.get(id=full_post_url)
        except Post.DoesNotExist:
            # Fallback to finding by internal_id
            try:
                post = Post.objects.get(internal_id=post_id)
            except Post.DoesNotExist:
                return Response({
                    'error': 'Post not found', 
                    'details': {
                        'full_url': full_post_url,
                        'author_id': author_id,
                        'post_id': post_id
                    }
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Get or create the author profile for the current user
        try:
            request_user_author = request.user.author
        except Author.DoesNotExist:
            request_user_author = Author.objects.create(
                user=request.user,
                type='author',
                displayName=request.user.username,
            )
        
        # Create the comment
        comment = Comment.objects.create(
            type='comment',
            post=post,
            author=request_user_author,
            content=content,
            published=timezone.now()
        )
        
        # Add comment to post
        post.comments.add(comment)
        
        # Prepare response data
        return Response({
            'id': comment.id,
            'content': comment.content,
            'published': comment.published.isoformat(),
            'author': {
                'id': comment.author.id,
                'displayName': comment.author.displayName
            },
            'post': {
                'id': post.id,
                'internal_id': post.internal_id
            }
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        # Log the full exception for server-side debugging
        import traceback
        traceback.print_exc()
        return Response({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CommentLikeView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request, author_id, post_id, comment_id):
        try:
            # Debug prints
            print("\n--- Comment Like Debugging ---")
            print(f"Request User: {request.user.username}")
            print(f"Raw Author ID: {author_id}")
            print(f"Raw Post ID: {post_id}")
            print(f"Raw Comment ID: {comment_id}")
            
            # Normalize author_id (remove URL if present)
            if isinstance(author_id, str) and '/authors/' in author_id:
                author_id = author_id.split('/authors/')[-1].split('/')[0]
            
            # Construct the full post URL
            full_post_url = f"http://localhost:8000/social/api/authors/{author_id}/posts/{post_id}"
            
            # Find the post
            try:
                # Try to find the post by its full URL ID first
                post = Post.objects.get(id=full_post_url)
            except Post.DoesNotExist:
                # Fallback to finding by internal_id
                try:
                    post = Post.objects.get(internal_id=post_id)
                except Post.DoesNotExist:
                    return Response({
                        'error': 'Post not found', 
                        'details': {
                            'full_url': full_post_url,
                            'author_id': author_id,
                            'post_id': post_id
                        }
                    }, status=status.HTTP_404_NOT_FOUND)
            
            # Find the comment
            try:
                comment = Comment.objects.get(id=comment_id)
            except Comment.DoesNotExist:
                return Response({
                    'error': 'Comment not found', 
                    'details': {
                        'comment_id': comment_id
                    }
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get or create the author profile for the current user
            try:
                request_user_author = request.user.author
            except Author.DoesNotExist:
                request_user_author = Author.objects.create(
                    user=request.user,
                    type='author',
                    displayName=request.user.username,
                )
            
            # Check if like already exists
            like_exists = comment.likes.filter(id=request_user_author.id).exists()
            
            if like_exists:
                # Unlike
                comment.likes.remove(request_user_author)
                action = 'unliked'
            else:
                # Like
                comment.likes.add(request_user_author)
                action = 'liked'
            
            return Response({
                'action': action,
                'like_count': comment.likes.count()
            })
        
        except Exception as e:
            # Log the full exception for server-side debugging
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'An unexpected error occurred',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)