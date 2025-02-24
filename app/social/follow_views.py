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
from .models import Follow, Author, FollowRequest, Inbox


class FollowersListView(APIView):
    """Manages the list of authors that are following an author."""
    
    def get(self, request, author_id):
        author_id = unquote(author_id)
        expected_author_id = f"{settings.HOST}api/authors/{author_id}"
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
        expected_author_id = f"{settings.HOST}api/authors/{author_id}"

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
        expected_author_id = f"{settings.HOST}api/authors/{author_id}"

        print(f" Checking if {expected_author_id} follows {follower_fqid}")

        # Ensure the follow relationship exists
        get_object_or_404(Follow, follower_id=follower_fqid, followee__id=expected_author_id)

        # Get the follower from the database
        follower = get_object_or_404(Author, id=follower_fqid)
        serializer = AuthorSerializer(follower)
        return Response(serializer.data, status=status.HTTP_200_OK)



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
    print(f" Available Authors to Follow: {[author.displayName for author in authors]}")

    return render(request, 'social/follow.html', {
        'authors': authors,
        'my_author': my_author, 
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
    my_author_id = my_author.id  #  Full author ID

    #  Find authors the user is following from the `Follow` table
    following_entries = Follow.objects.filter(follower_id=my_author_id)

    following_authors = []
    for follow in following_entries:
        try:
            response = requests.get(follow.followee.id, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            author_data = response.json()
            following_authors.append(author_data)
        except requests.exceptions.RequestException as e:
            print(f" Error fetching author {follow.followee.id}: {e}")

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
    """Shows a list of friends (mutual followers) of the logged-in user"""

    #  Get logged-in user
    if not hasattr(request.user, 'author'):
        return redirect('social:register')  # Redirect to register if no author profile

    my_author = request.user.author
    my_author_id = my_author.id

    print(f"Checking friends for: {my_author.displayName} ({my_author_id})")

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
            print(f" Error fetching friend details for {friend_id}: {e}")

    print(f" Found {len(friends)} friends")

    # Render `friends.html` and pass the friends list
    return render(request, "social/friends.html", {
        "my_author": my_author,
        "friends": friends
    })


