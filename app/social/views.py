from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView  # Moved to the correct place
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt

from .serializers import PostSerializer, AuthorSerializer
from .models import Post, Author, Follow, FollowRequest
import requests
from django.shortcuts import render, redirect, get_object_or_404
from .forms import PostForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.views import View
from django.contrib import messages
from urllib.parse import unquote
from django.db import transaction  # Correct placement of transaction import

import requests  # Correct placement of requests import
from django.conf import settings
import json
@login_required  # Now correctly placed above a view function
def stream(request):
    post_list = Post.objects.filter().order_by('-published')
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    return render(request, 'social/index.html', {'posts': posts})



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


class PostListCreateAPIView(generics.ListCreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user.author)




class FollowersListView(APIView):
    """Manages the list of authors that an author is following."""

    def get(self, request, author_id):
        """
        Retrieves a list of authors that are following AUTHOR_ID.
        """
        author_id = unquote(author_id)
        expected_author_id = f"{settings.HOST}api/authors/{author_id}"

        print(f"📥 Checking followers list for: {expected_author_id}")

        # Ensure the author exists
        author = get_object_or_404(Author, id=expected_author_id)

        # Get all authors that are following this author
        followers = Follow.objects.filter(followee=author)

        followers_list = []
        for follow in followers:
            follower_id = follow.follower_id  # Get follower ID

            # If follower is local, return full details from the DB
            if follower_id.startswith(settings.HOST):
                try:
                    follower = Author.objects.get(id=follower_id)
                    followers_list.append({
                        "id": follower.id,
                        "type": "author",
                        "displayName": follower.displayName,
                        "github": follower.github,
                        "profileImage": follower.profileImage,
                        "host": follower.host,
                    })
                except Author.DoesNotExist:
                    print(f" Error: Local follower {follower_id} not found!")
                    continue
            else:
                # If follower is remote, fetch details from their API
                try:
                    response = requests.get(follower_id, headers={"Content-Type": "application/json"})
                    response.raise_for_status()
                    data = response.json()

                    followers_list.append({
                        "id": data.get("id", follower_id),
                        "type": data.get("type", "author"),
                        "displayName": data.get("displayName", "Unknown"),
                        "github": data.get("github", ""),
                        "profileImage": data.get("profileImage", ""),
                        "host": data.get("host", ""),
                    })
                except requests.exceptions.RequestException as e:
                    print(f" Error fetching details for {follower_id}: {e}")
                    continue

        return Response({"type": "followers", "items": followers_list}, status=status.HTTP_200_OK)



    def put(self, request, author_id):
        """
        Approves a follow request by adding the author from the JSON body to the followers list.
        """
        author_id = author_id  # Already decoded
        expected_author_id = f"{settings.HOST}api/authors/{author_id}"

        print(f"Approving follow request for: {expected_author_id}")

        # Ensure the author exists
        author = get_object_or_404(Author, id=expected_author_id)

        # Parse JSON body
        data = request.data
        follower_id = data.get("id")

        if not follower_id:
            return Response({"error": "Missing follower ID in request body"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Check if the follow request exists
            follow_request = FollowRequest.objects.filter(
                followee=author, follower_id=follower_id, status="pending"
            ).first()

            if not follow_request:
                return Response({"error": "Follow request not found"}, status=status.HTTP_404_NOT_FOUND)

            # Approve request
            follow_request.status = "accepted"
            follow_request.save()

            # Store the follower
            Follow.objects.get_or_create(followee=author, follower_id=follower_id)

        return Response({"message": "Follow request approved"}, status=status.HTTP_200_OK)

    def delete(self, request, author_id):
        """
        Removes a follower from the author's followers list.
        The follower ID is expected in the request body.
        """
        author_id = unquote(author_id)
        expected_author_id = f"{settings.HOST}api/authors/{author_id}"

        print(f" Removing follower for: {expected_author_id}")

        # Ensure the author exists
        author = get_object_or_404(Author, id=expected_author_id)

        # Parse follower ID from request body
        data = request.data
        follower_fqid = data.get("id")

        if not follower_fqid:
            return Response({"error": "Missing follower ID"}, status=status.HTTP_400_BAD_REQUEST)

        print(f"🚨 Removing follower: {follower_fqid}")

        # Delete the follower
        deleted, _ = Follow.objects.filter(followee=author, follower_id=follower_fqid).delete()
        
        if deleted:
            return Response({"message": "Follower removed successfully"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Follower not found"}, status=status.HTTP_404_NOT_FOUND)
                

class FollowerDetailView(APIView):
    """Check if a user follows an author, add, or remove a follower"""

    def get(self, request, author_id, follower_fqid):
        """
        Checks if AUTHOR_SERIAL is following FOREIGN_AUTHOR_FQID.
        If true, makes a GET request to the author's followee ID and returns full author details.
        """
        author_id = unquote(author_id)
        follower_fqid = unquote(follower_fqid)

        expected_author_id = f"{settings.HOST}api/authors/{author_id}"

        print(f"📥 Checking if {expected_author_id} follows {follower_fqid}")

        # Ensure the author exists
        author = get_object_or_404(Follow, follower_id=follower_fqid, followee__id=expected_author_id)

        if author:
            print(f" {follower_fqid} is a follower of {expected_author_id}")

            # ✅ Make GET request to the followee's ID to fetch full author details
            try:
                response = requests.get(follower_fqid, headers={"Content-Type": "application/json"})
                response.raise_for_status()  # Raise error if status code is not 200
                author_data = response.json()

                # ✅ Construct response in the required format
                return Response({
                    "type": "author",
                    "id": author_data.get("id"),
                    "host": author_data.get("host"),
                    "displayName": author_data.get("displayName"),
                    "page": author_data.get("page"),
                    "github": author_data.get("github", ""),
                    "profileImage": author_data.get("profileImage", ""),
                }, status=status.HTTP_200_OK)

            except requests.exceptions.RequestException as e:
                print(f"Error fetching author details: {e}")
                return Response({"error": "Failed to retrieve author details"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        print(f"{follower_fqid} is NOT a follower of {expected_author_id}")
        return Response({"error": "Not a follower"}, status=status.HTTP_404_NOT_FOUND)

def inbox_view(request):
    return render(request, "social/inbox.html")

def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            if request.user.is_authenticated and hasattr(request.user, 'author'):
                post.author = request.user.author
            else:
                default_user, created = User.objects.get_or_create(
                    username='anonymous_user', defaults={'password': 'password'})
                post.author, created = Author.objects.get_or_create(
                    user=default_user,
                    defaults={
                        'id': f'http://localhost:8000/authors/{default_user.username}',
                        'displayName': 'Anonymous Author',
                        'host': 'http://localhost:8000',
                        'type': 'Author'
                    }
                )
            post.published = timezone.now()
            post.save()
            return redirect('social:index')
    else:
        form = PostForm()
    return render(request, 'social/create_post.html', {'form': form})


def update_post(request, id):
    post = get_object_or_404(Post, id=id)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('social:index')
    else:
        form = PostForm(instance=post)
    return render(request, 'social/update_post.html', {'form': form, 'post': post})


def delete_post(request, id):
    post = get_object_or_404(Post, id=id)
    if request.method == 'POST':
        post.is_deleted = True
        post.visibility = 'DELETED'
        post.save()
        return redirect('social:index')
    return render(request, 'social/delete_post.html', {'post': post})


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


def post_detail(request, auto_id):
    post = get_object_or_404(Post, auto_id=auto_id)
    return render(request, 'social/post_detail.html', {'post': post})


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

        # Extract only "follow" requests from inbox
        follow_requests = [item for item in inbox_data.get("items", []) if item.get("type", "").lower() == "follow"]

    except requests.exceptions.RequestException as e:  # Correct exception handling
        print(f" Error fetching inbox data: {e}")
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
        followee_id = data.get("followee_id")  # ✅ Get followee ID from request body
        if not followee_id:
            return JsonResponse({"error": "Missing followee ID"}, status=400)

        my_author = request.user.author  # ✅ Get logged-in author's profile

        # ✅ Delete the follow object
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

    # ✅ Get people I follow
    following_ids = set(Follow.objects.filter(follower_id=my_author_id).values_list("followee_id", flat=True))

    # ✅ Get people who follow me
    followers_ids = set(Follow.objects.filter(followee_id=my_author_id).values_list("follower_id", flat=True))

    # ✅ Find mutual followers (friends)
    friends_ids = following_ids.intersection(followers_ids)

    # ✅ Fetch full author details for friends
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
    
    """Handles follow requests in an author's inbox."""
    permission_classes = [AllowAny]
    from rest_framework.permissions import AllowAny

class InboxView(APIView):
    """Handles follow requests in an author's inbox."""

    permission_classes = [AllowAny]

    def post(self, request, author_id):
        """Receives and stores follow requests."""
        print(f"📥 Receiving follow request for: {author_id}")

        # Construct expected author ID
        local_author_id = f"{settings.HOST}api/authors/{author_id}"
        print(f"🔍 Expected Author ID: {local_author_id}")

        # Log the full incoming request data for debugging
        print(f"📥 Full request data: {request.data}")

        data = request.data

        # Ensure request type is "Follow"
        if data.get("type") != "Follow":
            print(f" Invalid request type: {data.get('type')}")
            return Response({"error": "Invalid request type"}, status=status.HTTP_400_BAD_REQUEST)

        actor_data = data.get("actor")
        object_data = data.get("object")

        # Validate presence of actor and object
        if not actor_data or not object_data:
            print(f" Missing actor or object")
            return Response({"error": "Missing actor or object"}, status=status.HTTP_400_BAD_REQUEST)

        follower_id = actor_data["id"]  # The one sending the request
        followee_id = object_data["id"]  # The one receiving the request

        print(f"🔍 Checking if {followee_id} is local or foreign...")

        # Check if the followee exists in our local database
        is_local = followee_id.startswith(settings.HOST)

        if is_local:
            # Followee is local, store the request in the inbox
            followee = get_object_or_404(Author, id=local_author_id)

            follow_request, created = FollowRequest.objects.get_or_create(
                followee=followee,
                follower_id=follower_id,  # Store FQID for remote followers
                defaults={"summary": data.get("summary", ""), "status": "pending"}
            )

            if not created:
                return Response({"error": "Follow request already exists"}, status=status.HTTP_409_CONFLICT)

            print(f" Follow request stored from {follower_id} to {followee.id}")
            return Response({"message": "Follow request received"}, status=status.HTTP_201_CREATED)

        else:
            # Followee is foreign, create the follow object immediately
            Follow.objects.get_or_create(followee_id=followee_id, follower_id=follower_id)

            print(f" Foreign followee detected! adding {follower_id} as a follower of {followee_id}")
            return Response({"message": "Follow request sent and assumed accepted"}, status=status.HTTP_201_CREATED)



    def get(self, request, author_id):
        """
        Fetches pending follow requests and retrieves full author details.
        """
        author_id = unquote(author_id)
        expected_author_id = f"{settings.HOST}api/authors/{author_id}"  # Ensure correct format

        print(f"📥 Checking inbox for: {expected_author_id}")  # Debugging output

        # Get the full author object
        author = get_object_or_404(Author, id=expected_author_id)

        # Get all pending follow requests
        follow_requests = FollowRequest.objects.filter(followee=author, status="pending")

        print(f"📌 Found {follow_requests.count()} pending follow requests")  # Debugging output

        # Fetch details for each author via API calls
        inbox_items = []
        for fr in follow_requests:
            follower_url = fr.follower_id  # The full follower URL (remote/local)
            followee_url = fr.followee.id  # The followee (local author's) full URL

            # ✅ Fetch follower details from API
            follower_data = self.get_author_details(follower_url)
            followee_data = self.get_author_details(followee_url)

            if follower_data and followee_data:  # Only include if both API calls succeed
                inbox_items.append({
                    "type": "follow",
                    "summary": f"{follower_data['displayName']} wants to follow {followee_data['displayName']}",
                    "actor": follower_data,
                    "object": followee_data
                })

        print(f"📤 Returning {len(inbox_items)} follow requests")  # Debugging output

        return Response({"type": "inbox", "items": inbox_items}, status=status.HTTP_200_OK)

    def get_author_details(self, author_url):
        """
        Fetches full author details from the provided author ID (URL).
        """
        try:
            response = requests.get(author_url, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            author_data = response.json()

            # ✅ Ensure correct format
            formatted_data = {
                "type": "author",
                "id": author_data.get("id", author_url),  # Use the URL if ID is missing
                "host": author_data.get("host", author_url.split("/authors/")[0] + "/"),
                "displayName": author_data.get("displayName", "Unknown"),
                "github": author_data.get("github", ""),
                "profileImage": author_data.get("profileImage", ""),
                "page": author_data.get("page", author_url.replace("/api/", "/")),
            }

            print(f" Fetched Author Data: {formatted_data}")  # Debugging output
            return formatted_data

        except requests.exceptions.RequestException as e:
            print(f" Error fetching author details for {author_url}: {e}")
            return None  # Return None if the API call fails



    def delete(self, request, author_id):
            """
            Denies a follow request by extracting follower ID from the request body.
            """
            author_id = unquote(author_id)
            expected_author_id = f"{settings.HOST}api/authors/{author_id}"
            author = get_object_or_404(Author, id=expected_author_id)

            try:
                data = request.data  # Extract body from DELETE request
                foreign_author_fqid = data.get("follower_id")

                if not foreign_author_fqid:
                    return Response({"error": "Missing follower ID in request body"}, status=status.HTTP_400_BAD_REQUEST)

                follow_request = FollowRequest.objects.filter(
                    follower_id=foreign_author_fqid,
                    followee=author,
                    status="pending"
                )

                if follow_request.exists():
                    follow_request.update(status="denied")  # Just update the status
                    return Response({"message": "Follow request denied"}, status=status.HTTP_200_OK)

                return Response({"error": "Follow request not found"}, status=status.HTTP_404_NOT_FOUND)
            
            except Exception as e:
                return JsonResponse({"error": f"Failed to process request: {str(e)}"}, status=400)
