from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView 
from rest_framework.permissions import AllowAny
from .serializers import PostSerializer, AuthorSerializer
from .models import Post, Author, Follow, FollowRequest,Inbox
import requests
from django.shortcuts import render, redirect, get_object_or_404
from .forms import PostForm, EditProfileForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.views import View
from django.contrib import messages
from urllib.parse import unquote
from django.db import transaction
from django.conf import settings
import json
import os

######################################
#           STREAM/INDEX AREA        
######################################
@login_required
def stream(request):
    posts = Post.objects.exclude(visibility='DELETED')  # exclude posts with 'DELETED' visibility
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
            return render(request, 'social/register.html')

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

@api_view(['GET', 'POST'])
def get_author(request, id):
    
    if request.GET:
        author = Author.objects.get(
            id=f"http://localhost:8000/social/api/authors/{id}")
        serializer = AuthorSerializer(author)
        return Response(serializer.data)


@api_view(['GET'])
def get_authors(request):
    authors = Author.objects.all()
    serializer = AuthorSerializer(authors, many=True)
    return Response(serializer.data)

@login_required
def profile_page(request, id):
    #Get the author
    currentAuthor = Author.objects.filter(id=f"http://localhost:8000/social/api/authors/{id}").get()
    
    #Get all the posts
    posts = Post.objects.filter(author=currentAuthor).values()
    
    #We need type
    postsToRender = []
    for post in posts:
        print(post["id"])
        postDict = {
            "title": post["title"],
            "image": post["image"],
            "content": post["content"],
            "contentType": post["contentType"],
            "description": post["description"],
            "id": post["internal_id"]
        }
        postsToRender.append(postDict)
        
    return render(request, 'social/profile.html', {"posts": postsToRender, "author":currentAuthor, 'profile_author_id':id})

@login_required
def profile_edit(request, id):
    if request.POST:
        author = Author.objects.filter(id = f"http://localhost:8000/social/api/authors/{id}").get()
        form = EditProfileForm(request.POST, request.FILES, instance=author)
        print("VALID")
        if form.is_valid():
            
            form.save()
            return redirect('social:profile_page', id=id)
    currentUser = request.user
    currentAuthor = Author.objects.filter(user=currentUser).get()
    form = EditProfileForm(request.POST, request.FILES, instance=currentAuthor)
    if str(id) != currentAuthor.id.split('/')[-1]:
        return redirect('social:profile_page', id=id)
    else:
        print("correct")
    return render(request, 'social/profile_edit.html', {'form': form})


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
    

@login_required
def create_post(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user.author  # Assuming the user has an Author profile
            post.save()
            return redirect('social:index')
    else:
        form = PostForm()
    return render(request, 'social/create_post.html', {'form': form})

@login_required
def delete_post(request, internal_id):
    post = get_object_or_404(Post, internal_id=internal_id, author__user=request.user)

    if request.method == "POST":
        # Set the visibility to DELETED instead of deleting the post
        post.visibility = 'DELETED'
        post.save()

        return redirect('social:index')
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