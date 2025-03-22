from .serializers import AuthorSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import render, redirect, get_object_or_404
from urllib.parse import unquote
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import requests
from django.db import transaction
import json
from django.http import JsonResponse
from .models import Follow, Author, FollowRequest, Inbox, Node
from requests.auth import HTTPBasicAuth
from .utils import get_base_url 
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated




from urllib.parse import urljoin

def fetch_remote_authors_view(request):
    if not hasattr(request.user, 'author'):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    node_url = request.GET.get("node")
    if not node_url:
        return JsonResponse({"error": "Missing node parameter"}, status=400)

    print(f"[DEBUG] Fetching remote authors from: {node_url}")

    try:
        #for now this only works if the username and password belongs to someone in our node because the api can only be viewed if that user is the author in our node.
        username = "abc"
        password = "abc"
        my_author_id = request.user.author.id

        response = requests.get(
            urljoin(node_url, "authors/"),
            auth=HTTPBasicAuth(username, password),
            headers={"Accept": "application/json"},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            remote_authors = data
        else:
            remote_authors = data.get("items") or data.get("authors") or []

        # Get IDs of authors already followed or requested
        requested_ids = set(
            FollowRequest.objects.filter(follower_id=my_author_id)
            .values_list("followee__id", flat=True)
        )
        followed_ids = set(
            Follow.objects.filter(follower_id=my_author_id)
            .values_list("followee__id", flat=True)
        )
        blocked_ids = requested_ids.union(followed_ids)

        # Filter out authors already requested or followed
        filtered_authors = [
            author for author in remote_authors
            if author.get("id") not in blocked_ids
        ]

        print(f"[DEBUG] Returning {len(filtered_authors)} authors after filtering.")
        return JsonResponse({"authors": filtered_authors})

    except Exception as e:
        print(f"[ERROR] Failed to fetch authors: {e}")
        return JsonResponse({"error": str(e)}, status=500)




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def local_follow_finalize(request):
    """Creates a Follow object and accepted FollowRequest immediately after sending remote follow"""
    follower = request.user.author
    data = request.data
    followee_id = data.get("followee_id")
    summary = data.get("summary", "")

    if not followee_id:
        return Response({"error": "Missing followee_id"}, status=400)

    author, _ = Author.objects.get_or_create(
        id=followee_id,
        defaults={
            "displayName": data.get("displayName", "Unknown"),
            "host": data.get("host", ""),
            "github": data.get("github", ""),
            "profileImage": data.get("profileImage", ""),
            "page": data.get("page", "")
        }
    )

    Follow.objects.get_or_create(follower_id=follower.id, followee=author)

    FollowRequest.objects.update_or_create(
        follower_id=follower.id,
        followee=author,
        defaults={"status": "accepted", "summary": summary}
    )

    return Response({"message": "Follow stored locally as accepted."})


class FollowersListView(APIView):
    """Manages the list of authors that are following an author."""
    
    def get(self, request, author_id):
        author_id = unquote(author_id)
        expected_author_id = f"http://{request.get_host()}/social/api/authors/{author_id}"
        author = get_object_or_404(Author, id=expected_author_id)
        followers = Follow.objects.filter(followee=author)
        
        followers_list = []
        for follow in followers:
            follower_id = follow.follower_id  # Follower ID
            # For local authors:
            try:
                local_follower = Author.objects.get(id=follower_id)
                serializer = AuthorSerializer(local_follower)
                followers_list.append(serializer.data)
            except Author.DoesNotExist:
                    continue

        return Response({"type": "followers", "items": followers_list}, status=status.HTTP_200_OK)




    def put(self, request, author_id):
        """
        Approves a follow request by adding the author from the JSON body to the followers list.
        """
        author_id = unquote(author_id)
        expected_author_id = f"http://{request.get_host()}/social/api/authors/{author_id}"

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

            #  DELETE from inbox (remove request after approval)
            inbox = Inbox.objects.filter(author=author).first()
            if inbox:
                inbox.inbox_follows.remove(follow_request)
                print(f" Removed follow request from inbox: {follower_id} -> {author_id}")

        return Response({"message": "Follow request approved and removed from inbox"}, status=status.HTTP_200_OK)


    def delete(self, request, author_id):
        """
        Removes a follower from the author's followers list.
        The follower ID is expected in the request body.
        """
        author_id = unquote(author_id)
        expected_author_id = f"http://{request.get_host()}/social/api/authors/{author_id}"

        print(f" Removing follower for: {expected_author_id}")

        # Ensure the author exists
        author = get_object_or_404(Author, id=expected_author_id)

        # Parse follower ID from request body
        data = request.data
        follower_fqid = data.get("id")

        if not follower_fqid:
            return Response({"error": "Missing follower ID"}, status=status.HTTP_400_BAD_REQUEST)

        print(f"Removing follower: {follower_fqid}")

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
        Checks if the given follower (follower_fqid) is following the author.
        If so, retrieves the follower details from the database using AuthorSerializer.
        """
        author_id = unquote(author_id)
        follower_fqid = unquote(follower_fqid)
        expected_author_id = f"http://{request.get_host()}/social/api/authors/{author_id}"

        print(f" Checking if {expected_author_id} follows {follower_fqid}")

        # Ensure the follow relationship exists
        get_object_or_404(Follow, follower_id=follower_fqid, followee__id=expected_author_id)

        # Get the follower from the database
        follower = get_object_or_404(Author, id=follower_fqid)
        serializer = AuthorSerializer(follower)
        return Response(serializer.data, status=status.HTTP_200_OK)



def follow_view(request):
    """Shows a list of authors to follow, excluding those already requested and from other nodes"""

    if not hasattr(request.user, 'author'):
        return redirect('social:register')

    my_author = request.user.author
    self_host = get_base_url(request)  # e.g., http://localhost:8000

    # Get IDs of authors already followed or requested
    requested_authors = FollowRequest.objects.filter(
        follower_id=my_author.id
    ).values_list('followee__id', flat=True)

    # Filter only local authors (same host)
    authors = Author.objects.filter(
        host__startswith=self_host
    ).exclude(
        id=my_author.id
    ).exclude(
        id__in=requested_authors
    )

    print(f"[DEBUG] Authors on host '{self_host}': {[a.displayName for a in authors]}")

    nodes = Node.objects.filter(enabled=True)

    return render(request, 'social/follow.html', {
        'authors': authors,
        'my_author': my_author,
        'nodes': nodes
    })



def followers_view(request):
    """Shows the list of followers of the logged-in user with a delete option."""
    
    if not hasattr(request.user, 'author'):
        return redirect('social:register')  # Redirect if no author profile

    my_author = request.user.author  # Get logged-in author's profile
    my_author_id = my_author.id  # Full author ID

    # Fetch all follow records where the logged-in user is the followee.
    follows = Follow.objects.filter(followee=my_author)
    
    followers_list = []
    for follow in follows:
        try:
            # Assume that Follow.follower is a ForeignKey to Author.
            follower_id = follow.follower_id
            follower = Author.objects.get(id=follower_id)
            serializer = AuthorSerializer(follower)
            followers_list.append(serializer.data)
        except Author.DoesNotExist:
            print(f"Local follower {follow.follower_id} not found in database.")
            continue

    return render(request, "social/followers.html", {
        "my_author_id": my_author_id,
        "followers": followers_list,
    })


def following_view(request):
    """Shows a list of authors that the logged-in user is following with an unfollow option."""

    if not hasattr(request.user, 'author'):
        return redirect('social:register')  # Redirect if no author profile

    my_author = request.user.author  # Get logged-in author's profile
    my_author_id = my_author.id  # Full author ID

    #  Find authors the user is following from the `Follow` table and get their author objects
    following_entries = Follow.objects.filter(follower_id=my_author_id).select_related('followee')

    following_authors = [follow.followee for follow in following_entries]  # Retrieve author objects

    return render(request, "social/following.html", {
        "my_author_id": my_author_id,
        "following_authors": following_authors,  # List of followed authors
    })

def unfollow_view(request):
    """Handles unfollowing an author by deleting the follow object in the database."""

    print(" Unfollow request received. User:", request.user)

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
        print("Unfollowing:", followee_id, "from author:", my_author.id)

        # Delete the follow object
        deleted, _ = Follow.objects.filter(follower_id=my_author.id, followee__id=followee_id).delete()

        if deleted:
            return JsonResponse({"message": "Unfollowed successfully"}, status=200)
        else:
            return JsonResponse({"error": "Not following this author"}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)


def friends_view(request):
    """Shows a list of friends (mutual followers) of the logged-in user."""

    #  Get logged-in user
    if not hasattr(request.user, 'author'):
        return redirect('social:register')  # Redirect to register if no author profile

    my_author = request.user.author  # Get logged-in author's profile
    my_author_id = my_author.id

    print(f"Checking friends for: {my_author.displayName} ({my_author_id})")

    # Use the `friends` property from the `Author` model
    friends = my_author.friends.all()  # QuerySet of mutual followers

    print(f"Found {friends.count()} friends")

    # Render `friends.html` and pass the friends list
    return render(request, "social/friends.html", {
        "my_author": my_author,
        "friends": friends
    })