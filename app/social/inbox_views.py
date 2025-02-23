from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.shortcuts import render, redirect, get_object_or_404
from urllib.parse import unquote
from django.db import transaction
import requests
import json
from django.conf import settings
from .models import Author, Post, FollowRequest, Inbox, Like, Comment



def follow_inbox_view(request):
    """Fetches the inbox and filters only follow requests."""
    
    if not hasattr(request.user, 'author'):
        return redirect('social:register')  # Redirect if the user has no author profile

    my_author = request.user.author  # Get the logged-in author's profile
    my_author_id = my_author.id
    print(f" Logged-in Author ID: {my_author_id}")  # Debugging: See Author ID in logs

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
        print(f"Error fetching inbox data: {e}")
        follow_requests = []

    return render(request, "social/followInbox.html", {
        "my_author_id": my_author_id,
        "follow_requests": follow_requests  # follow requests passed to the template
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

        print(f"Fetching inbox for: {expected_author_id}")

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

        print(f"Returning {len(inbox_items)} items in the inbox.")
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
            print(f" Error fetching author details for {author_url}: {e}")
            return None

    def get_post_details(self, post_url):
        """Fetches post details from an API."""
        try:
            response = requests.get(post_url, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f" Error fetching post details for {post_url}: {e}")
            return None

    def get_like_details(self, like_url):
        """Fetches like details from an API."""
        try:
            response = requests.get(like_url, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f" Error fetching like details for {like_url}: {e}")
            return None

    def get_comment_details(self, comment_url):
        """Fetches comment details from an API."""
        try:
            response = requests.get(comment_url, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f" Error fetching comment details for {comment_url}: {e}")
            return None

    def post(self, request, author_id):
        """Stores any incoming request (posts, likes, comments, follows) in the inbox."""

        author_id = unquote(author_id)
        expected_author_id = f"{settings.HOST}api/authors/{author_id}"

        print(f"Receiving new inbox item for: {expected_author_id}")

        author = get_object_or_404(Author, id=expected_author_id)
        inbox, created = Inbox.objects.get_or_create(author=author)

        data = request.data
        item_type = data.get("type")

        if item_type == "Follow":
            actor_data = data.get("actor", {})
            follower_id = actor_data.get("id")
            if not follower_id:
                return Response({"error": "Missing actor id"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if the foreign author (follower) exists; if not, add them.
            follower, created = Author.objects.update_or_create(
                id=follower_id,
                defaults={
                    "host": actor_data.get("host", ""),
                    "displayName": actor_data.get("displayName", ""),
                    "github": actor_data.get("github", ""),
                    "profileImage": actor_data.get("profileImage", ""),
                    "page": actor_data.get("page", "")
                }
            )

            follow_request, _ = FollowRequest.objects.get_or_create(
                followee=author,
                follower_id=follower_id,
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
        print(f" Stored {item_type} in inbox.")
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
                    follow_request.status = "denied"  #  Keep it in FollowRequest, just update status
                    follow_request.save()

                    # Remove from Inbox but keep in FollowRequest
                    Inbox.objects.filter(inbox_follows=follow_request).delete()

                    print(f" Denied follow request and removed from inbox: {foreign_author_fqid}")
                    return Response({"message": "Follow request denied and removed from inbox"}, status=status.HTTP_200_OK)

                return Response({"error": "Follow request not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": f"Failed to process request: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def inbox_view(request):
    return render(request, "social/inbox.html")