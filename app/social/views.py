from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import PostSerializer, AuthorSerializer

from .models import Post, Author, Follow,FollowRequest

from .serializers import PostSerializer

from django.shortcuts import render, redirect, get_object_or_404
from .forms import PostForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Author
from django.core.paginator import Paginator
from django.views import View
from django.contrib import messages


@login_required
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from urllib.parse import unquote
from django.db import transaction  # ✅ Import transaction


import requests  # ✅ Add this import
from django.conf import settings



def stream(request):
    post_list = Post.objects.filter(is_deleted=False).order_by('-published')
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

        # ✅ Get all authors that are following this author
        followers = Follow.objects.filter(followee=author)

        followers_list = []
        for follow in followers:
            follower_id = follow.follower_id  # ✅ Get follower ID

            # ✅ If follower is local, return only `author_id`
            if follower_id.startswith(settings.HOST):
                follower_id = follower_id.replace(f"{settings.HOST}api/authors/", "")

            followers_list.append({
                "id": follower_id,  # ✅ Local followers store only `author_id`, remote ones keep full URL
                "type": "author"
            })

        return Response({"type": "followers", "items": followers_list}, status=status.HTTP_200_OK)


    def put(self, request, author_id):
        """
        Approves a follow request by adding the author from the JSON body to the followers list.
        """
        author_id = author_id  # Already decoded
        expected_author_id = f"{settings.HOST}api/authors/{author_id}"

        print(f"✅ Approving follow request for: {expected_author_id}")

        # ✅ Ensure the author exists
        author = get_object_or_404(Author, id=expected_author_id)

        # ✅ Parse JSON body
        data = request.data
        follower_id = data.get("id")

        if not follower_id:
            return Response({"error": "Missing follower ID in request body"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # ✅ Check if the follow request exists
            follow_request = FollowRequest.objects.filter(
                followee=author, follower_id=follower_id, status="pending"
            ).first()

            if not follow_request:
                return Response({"error": "Follow request not found"}, status=status.HTTP_404_NOT_FOUND)

            # ✅ Approve request
            follow_request.status = "accepted"
            follow_request.save()

            # ✅ Store the follower
            Follow.objects.get_or_create(followee=author, follower_id=follower_id)

        return Response({"message": "Follow request approved"}, status=status.HTTP_200_OK)

    def delete(self, request, author_id, following_fqid):
        """
        Removes FOREIGN_AUTHOR_FQID from the list of authors AUTHOR_SERIAL is following.
        """
        author_id = unquote(author_id)
        following_fqid = unquote(following_fqid)

        expected_author_id = f"{settings.HOST}api/authors/{author_id}"

        print(f"❌ Removing {expected_author_id} from following {following_fqid}")

        author = get_object_or_404(Author, id=expected_author_id)
        followee = get_object_or_404(Author, id=following_fqid)

        deleted, _ = Follow.objects.filter(followee=followee, follower_id=expected_author_id).delete()
        if deleted:
            return Response({"message": "Unfollowed successfully"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Not following"}, status=status.HTTP_404_NOT_FOUND)


class FollowerDetailView(APIView):
    """Check if a user follows an author, add, or remove a follower"""

    def get(self, request, author_id, follower_fqid):
        """
        Checks if AUTHOR_SERIAL is following FOREIGN_AUTHOR_FQID.
        """
        author_id = unquote(author_id)
        follower_fqid = unquote(follower_fqid)

        expected_author_id = f"{settings.HOST}api/authors/{author_id}"

        print(f"📥 Checking if {expected_author_id} follows {follower_fqid}")

        author = get_object_or_404(Author, id=expected_author_id)
        follower_exists = Follow.objects.filter(follower_id=follower_fqid, followee__id=expected_author_id).exists()

        if follower_exists:
            return Response(status=status.HTTP_200_OK)
        else:
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


def update_post(request, auto_id):
    post = get_object_or_404(Post, auto_id=auto_id)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('social:index')
    else:
        form = PostForm(instance=post)
    return render(request, 'social/update_post.html', {'form': form, 'post': post})


def delete_post(request, auto_id):
    post = get_object_or_404(Post, auto_id=auto_id)
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
    """Shows a list of authors to follow"""
    my_author_id = settings.MY_AUTHOR_ID  # ✅ Fetch sender from settings.py

    # ✅ Get sender's full details from the database
    try:
        my_author = Author.objects.get(id=my_author_id)
    except Author.DoesNotExist:
        my_author = None  # ✅ If the author does not exist, set to None

    # ✅ Exclude sender from the follow list
    authors = Author.objects.exclude(id=my_author_id) if my_author else Author.objects.all()

    return render(request, 'social/follow.html', {
        'authors': authors,
        'my_author': my_author  # ✅ Pass sender details to template
    })





def follow_inbox_view(request):
    """Fetches the inbox and filters only follow requests."""
    
    # ✅ Get the current author's ID from settings.py
    my_author_id = settings.MY_AUTHOR_ID  

    # ✅ Construct the API URL for retrieving inbox data
    inbox_url = f"{my_author_id}/inbox"

    try:
        response = requests.get(inbox_url, headers={"Content-Type": "application/json"})
        response.raise_for_status()  # ✅ Ensure non-200 responses raise an error
        inbox_data = response.json()

        # ✅ Extract only "follow" requests from inbox
        follow_requests = [item for item in inbox_data.get("items", []) if item.get("type", "").lower() == "follow"]

    except requests.exceptions.RequestException as e:  # ✅ Correct exception handling
        print(f"❌ Error fetching inbox data: {e}")
        follow_requests = []

    return render(request, "social/followInbox.html", {
        "my_author_id": my_author_id,
        "follow_requests": follow_requests  # ✅ Only follow requests are passed to the template
    })


def followers_view(request):
    return render(request, "social/followers.html")





class InboxView(APIView):
    """Handles follow requests in an author's inbox."""

    def post(self, request, author_id):
        """Receives and stores follow requests."""

        print(f"📥 Receiving follow request for: {author_id}")

        # Construct expected author ID
        local_author_id = f"{settings.HOST}api/authors/{author_id}"
        print(f"🔍 Expected Author ID: {local_author_id}")

        # Log the full incoming request data for debugging
        print(f"📥 Full request data: {request.data}")  # ✅ This will show us what was received

        # Ensure the followee exists
        followee = get_object_or_404(Author, id=local_author_id)

        data = request.data

        # Ensure request type is "Follow"
        if data.get("type") != "Follow":
            print(f"❌ Invalid request type: {data.get('type')}")  # Debugging
            return Response({"error": "Invalid request type"}, status=status.HTTP_400_BAD_REQUEST)

        actor_data = data.get("actor")
        object_data = data.get("object")

        # Validate presence of actor and object
        if not actor_data or not object_data:
            print(f"❌ Missing actor or object")  # Debugging
            return Response({"error": "Missing actor or object"}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the object (followee) matches our local author
        if object_data.get("id") != local_author_id:
            print(f"❌ Followee ID mismatch. Expected: {local_author_id}, Received: {object_data.get('id')}")  # Debugging
            return Response({"error": "Followee ID mismatch"}, status=status.HTTP_400_BAD_REQUEST)

        # Store follow request
        follow_request, created = FollowRequest.objects.get_or_create(
            followee=followee,
            follower_id=actor_data["id"],
            defaults={"summary": data.get("summary", ""), "status": "pending"}
        )

        if not created:
            return Response({"error": "Follow request already exists"}, status=status.HTTP_409_CONFLICT)

        print(f"✅ Follow request stored from {actor_data['id']} to {followee.id}")
        return Response({"message": "Follow request received"}, status=status.HTTP_201_CREATED)


    def get(self, request, author_id):
        """
        Retrieves all pending follow requests.
        """
        author_id = unquote(author_id)
        expected_author_id = f"{settings.HOST}api/authors/{author_id}"  # ✅ Ensures correct format

        print(f"📥 Checking inbox for: {expected_author_id}")  # ✅ Debugging output

        # Ensure we are searching for the FULL author ID
        author = get_object_or_404(Author, id=expected_author_id)

        follow_requests = FollowRequest.objects.filter(followee=author, status="pending")

        inbox_items = [
            {
                "type": "follow",
                "summary": f"{fr.follower_id} wants to follow {fr.followee.displayName}",
                "actor": {
                    "type": "author",
                    "id": fr.follower_id,
                },
                "object": {
                    "type": "author",
                    "id": fr.followee.id,
                    "displayName": fr.followee.displayName,
                }
            }
            for fr in follow_requests
        ]

        return Response({"type": "inbox", "items": inbox_items}, status=status.HTTP_200_OK)



    def delete(self, request, author_id, foreign_author_fqid):
            """
            Denies a follow request and removes it from the inbox without making an API request.
            """
            author_id = unquote(author_id)
            foreign_author_fqid = unquote(foreign_author_fqid)
            expected_author_id = f"{settings.HOST}api/authors/{author_id}"

            author = get_object_or_404(Author, id=expected_author_id)

            follow_request = FollowRequest.objects.filter(
                follower_id=foreign_author_fqid,
                followee=author,
                status="pending"
            )

            if follow_request.exists():
                follow_request.update(status="denied")  # ✅ Just update the status
                return Response({"message": "Follow request denied"}, status=status.HTTP_200_OK)

            return Response({"error": "Follow request not found"}, status=status.HTTP_404_NOT_FOUND)



# from django.http import JsonResponse, HttpResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.utils.decorators import method_decorator
# from django.views import View
# from urllib.parse import unquote
# import json
# import requests  # For making HTTP requests to remote nodes

# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import AllowAny
# from rest_framework import status  

# from .models import Follow, Author
# from .serializers import FollowRequestSerializer  # Ensure you have this serializer



# @method_decorator(csrf_exempt, name='dispatch')
# class FollowersView(View):

#     def get(self, request, author_id):
#         """
#         Returns a list of authors following the given author.
#         """
#         decoded_author_id = unquote(author_id)  # Decode percent encoding
#         print(f"🔍 Received author_id: {author_id}")
#         print(f"🔍 Decoded author_id: {decoded_author_id}")

#         author = get_object_or_404(Author, id=decoded_author_id)
#         print(f"✅ Found author: {author.displayName}")

#         followers = Follow.objects.filter(followee=author, status="accepted")

#         follower_list = [
#             {
#                 "type": "author",
#                 "id": follower.follower.id,
#                 "host": follower.follower.host,
#                 "displayName": follower.follower.displayName,
#                 "github": follower.follower.github,
#                 "profileImage": follower.follower.profileImage,
#                 "page": follower.follower.page,
#             }
#             for follower in followers
#         ]

#         print(f"✅ Followers found: {len(follower_list)}")
#         return JsonResponse({"type": "followers", "followers": follower_list}, status=200)
 

# @method_decorator(csrf_exempt, name='dispatch')
# class FollowerDetailView(View):

#     def get(self, request, author_id, foreign_author_fqid):
#         """
#         Check if FOREIGN_AUTHOR_FQID is a follower of AUTHOR_SERIAL.
#         """
#         # Decode the percent-encoded URLs
#         author_id = unquote(author_id)
#         foreign_author_fqid = unquote(foreign_author_fqid)

#         print(f"🔍 Checking if {foreign_author_fqid} follows {author_id}")

#         # Ensure the author exists
#         author = get_object_or_404(Author, id=author_id)

#         # Check if foreign author is a follower
#         follower = Follow.objects.filter(
#             followee=author, 
#             follower__id=foreign_author_fqid, 
#             status="accepted"
#         ).first()

#         if follower:
#             response_data = {
#                 "type": "author",
#                 "id": follower.follower.id,
#                 "host": follower.follower.host,
#                 "displayName": follower.follower.displayName,
#                 "github": follower.follower.github,
#                 "profileImage": follower.follower.profileImage,
#                 "page": follower.follower.page,
#             }
#             return JsonResponse(response_data, status=200)

#         return JsonResponse({"error": "Not Found"}, status=404)

#     def put(self, request, author_id, foreign_author_fqid):
#         """
#         Accepts a follow request from FOREIGN_AUTHOR_FQID to AUTHOR_SERIAL.
#         """
#         # Decode the percent-encoded URLs
#         author_id = unquote(author_id)
#         foreign_author_fqid = unquote(foreign_author_fqid)

#         print(f"🔍 Accepting follow request from {foreign_author_fqid} to {author_id}")

#         # Ensure the author exists
#         author = get_object_or_404(Author, id=author_id)

#         # Check if the follow request exists and is pending
#         follow_request = Follow.objects.filter(
#             follower__id=foreign_author_fqid, 
#             followee=author, 
#             status="pending"
#         ).first()

#         if follow_request:
#             follow_request.status = "accepted"
#             follow_request.save()
#             return JsonResponse({"message": "Follow request accepted"}, status=200)

#         return JsonResponse({"error": "Follow request not found or already accepted"}, status=404)

#     def delete(self, request, author_id, foreign_author_fqid):
#         """
#         Removes FOREIGN_AUTHOR_FQID as a follower of AUTHOR_SERIAL.
#         """
#         # Decode the percent-encoded URLs
#         author_id = unquote(author_id)
#         foreign_author_fqid = unquote(foreign_author_fqid)

#         print(f"🔍 Removing {foreign_author_fqid} as a follower of {author_id}")

#         # Ensure the author exists
#         author = get_object_or_404(Author, id=author_id)

#         # Check if the follow relationship exists
#         follow_request = Follow.objects.filter(followee=author, follower__id=foreign_author_fqid, status="accepted")

#         if follow_request.exists():
#             follow_request.delete()
#             return JsonResponse({"message": "Follower removed"}, status=200)

#         return JsonResponse({"error": "Not Found"}, status=404)


# @method_decorator(csrf_exempt, name='dispatch')
# class InboxView(View):

#     def post(self, request, author_id):
#         """
#         Handles incoming follow requests to an author's inbox.
#         """
#         author_id = unquote(author_id)  # Decode percent-encoded URLs
#         print(f"📥 Receiving follow request for: {author_id}")

#         # Ensure the recipient author exists
#         author = get_object_or_404(Author, id=author_id)

#         try:
#             data = json.loads(request.body)
#         except json.JSONDecodeError:
#             return JsonResponse({"error": "Invalid JSON"}, status=400)

#         if data.get("type") != "follow":
#             return JsonResponse({"error": "Invalid request type"}, status=400)

#         actor_data = data.get("actor")
#         object_data = data.get("object")

#         if not actor_data or not object_data:
#             return JsonResponse({"error": "Missing actor or object"}, status=400)

#         actor_id = actor_data.get("id")
#         object_id = object_data.get("id")

#         # Ensure the follow request is actually for the correct author
#         if object_id != author_id:
#             return JsonResponse({"error": "Follow request object does not match target author"}, status=400)

#         print(f"🔍 Follow request from {actor_id} to {object_id}")

#         # Ensure the follower exists (create if not)
#         follower, _ = Author.objects.get_or_create(
#             id=actor_id,
#             defaults={
#                 "displayName": actor_data.get("displayName", "Unknown"),
#                 "host": actor_data.get("host", ""),
#                 "github": actor_data.get("github", ""),
#                 "profileImage": actor_data.get("profileImage", ""),
#                 "page": actor_data.get("page", ""),
#             }
#         )

#         # Store follow request in database as PENDING
#         follow_request, created = Follow.objects.get_or_create(
#             follower=follower,
#             followee=author,
#             defaults={"status": "pending", "summary": data.get("summary", "Follow request")}
#         )

#         if not created:
#             return JsonResponse({"message": "Follow request already exists"}, status=200)

#         return JsonResponse({"message": "Follow request received"}, status=201)

#     def get(self, request, author_id):
#         """
#         Retrieve pending follow requests from the inbox.
#         """
#         author_id = unquote(author_id)  # Decode percent-encoded URL
#         print(f"📥 Checking inbox for: {author_id}")

#         author = get_object_or_404(Author, id=author_id)
#         follow_requests = Follow.objects.filter(followee=author, status="pending")

#         inbox_items = [
#             {
#                 "type": "follow",
#                 "summary": f"{fr.follower.displayName} wants to follow {fr.followee.displayName}",
#                 "actor": {
#                     "type": "author",
#                     "id": fr.follower.id,
#                     "host": fr.follower.host,
#                     "displayName": fr.follower.displayName,
#                     "github": fr.follower.github,
#                     "profileImage": fr.follower.profileImage,
#                     "page": fr.follower.page,
#                 },
#                 "object": {
#                     "type": "author",
#                     "id": fr.followee.id,
#                     "host": fr.followee.host,
#                     "displayName": fr.followee.displayName,
#                     "github": fr.followee.github,
#                     "profileImage": fr.followee.profileImage,
#                     "page": fr.followee.page,
#                 }
#             }
#             for fr in follow_requests
#         ]

#         return JsonResponse({"type": "inbox", "items": inbox_items}, status=200)

# @method_decorator(csrf_exempt, name='dispatch')
# class FollowRequestView(View):

#     def post(self, request, author_id):
#         """
#         Handles when AUTHOR_ID sends a follow request to another author.
#         Stores the request locally and sends a request to the recipient's inbox.
#         """
#         author_id = unquote(author_id)  # Decode percent-encoded URLs
#         print(f"📤 Sending follow request from: {author_id}")

#         try:
#             data = json.loads(request.body)
#         except json.JSONDecodeError:
#             return JsonResponse({"error": "Invalid JSON"}, status=400)

#         if data.get("type") != "follow":
#             return JsonResponse({"error": "Invalid request type"}, status=400)

#         actor_data = data.get("actor")
#         object_data = data.get("object")

#         if not actor_data or not object_data:
#             return JsonResponse({"error": "Missing actor or object"}, status=400)

#         actor_id = actor_data.get("id")
#         object_id = object_data.get("id")

#         print(f"📤 Follow request from {actor_id} to {object_id}")

#         follower, _ = Author.objects.get_or_create(
#             id=actor_id,
#             defaults={
#                 "displayName": actor_data.get("displayName", "Unknown"),
#                 "host": actor_data.get("host", ""),
#                 "github": actor_data.get("github", ""),
#                 "profileImage": actor_data.get("profileImage", ""),
#                 "page": actor_data.get("page", ""),
#             }
#         )

#         followee = get_object_or_404(Author, id=object_id)

#         # Store follow request as PENDING
#         follow_request, created = Follow.objects.get_or_create(
#             follower=follower,
#             followee=followee,
#             defaults={"status": "pending", "summary": data.get("summary", "Follow request")}
#         )

#         if not created:
#             return JsonResponse({"message": "Follow request already exists"}, status=200)

#         # **Post follow request to the recipient's inbox**
#         inbox_url = f"{followee.host}api/authors/{object_id}/inbox/"
#         print(f"📩 Posting follow request to recipient's inbox: {inbox_url}")

#         try:
#             response = requests.post(inbox_url, json=data, headers={"Content-Type": "application/json"})
#             if response.status_code in [200, 201]:
#                 print("✅ Follow request successfully posted to inbox.")
#                 return JsonResponse({"message": "Follow request sent"}, status=201)
#             else:
#                 print(f"❌ Failed to post to inbox. Status Code: {response.status_code}")
#                 return JsonResponse({"error": "Failed to send follow request to inbox"}, status=500)
#         except requests.exceptions.RequestException as e:
#             print(f"❌ Error sending request to inbox: {e}")
#             return JsonResponse({"error": "Failed to send request to recipient's inbox"}, status=500)
