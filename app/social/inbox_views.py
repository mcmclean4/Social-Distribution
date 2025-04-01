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
from django.utils import timezone
from .models import Author, Post, FollowRequest, Inbox, Like, Comment, Node, Follow
from .authentication import NodeBasicAuthentication
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse


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
    authentication_classes = [NodeBasicAuthentication, BasicAuthentication]

    def get(self, request, author_id):
        """
        Fetches all items (posts, likes, comments, follow requests) in the inbox.
        """
        author_id = unquote(author_id)
        expected_author_id = f"http://{request.get_host()}/social/api/authors/{author_id}"

        print(f"Fetching inbox for: {expected_author_id}")

        # Get the author's inbox
        author = get_object_or_404(Author, id=expected_author_id)
        inbox = Inbox.objects.filter(author=author).first()

        if not inbox:
            return Response({"type": "inbox", "items": []}, status=status.HTTP_200_OK)

        inbox_items = []

        # Process follow requests
        for fr in inbox.inbox_follows.all():
            follower_data = self.format_author(get_object_or_404(Author, id=fr.follower_id))
            followee_data = self.format_author(fr.followee)

            if follower_data and followee_data:
                inbox_items.append({
                    "type": "Follow",
                    "summary": f"{follower_data['displayName']} wants to follow {followee_data['displayName']}",
                    "actor": follower_data,
                    "object": followee_data
                })

        # Process posts
        for post in inbox.inbox_posts.all():
            inbox_items.append(self.format_post(post, author_id))

        # Process likes using `format_likes()`
        # Process each like individually
        for like in inbox.inbox_likes.all():
            inbox_items.append(self.format_like(like))


        # Process comments using `format_comments()`
        for comment in inbox.inbox_comments.all():
            inbox_items.append(self.format_comments(comment))

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

    def format_author(self,author):
        """Returns the formatted author object."""
        return {
            "type": "author",
            "id": author.id,
            "host": author.host,
            "displayName": author.displayName,
            "github": author.github if author.github else "",
            "profileImage": author.profileImage if author.profileImage else "",
            "page": author.page if author.page else ""
        }

    def format_like(self, like):
        """Returns formatted likes for the inbox."""
        return {
            "type": "like",
            "id": like.id,
            "published": like.published.isoformat(),
            "author": self.format_author(like.author),
            "object": like.object,  # This is now a URLField (string)
        }


    def format_comments(self, comments):
        """Format comments for a post"""
        comments_list = []
        
        # Handle if we're passed a single post instead of comments
        if isinstance(comments, Post):
            # Get comments for this post
            comments = comments.comments.all()
        # Handle if we're passed a single comment
        elif isinstance(comments, Comment):
            # Create a single-item list with this comment
            return {
                "type": "comment",
                "id": comments.id,
                "author": self.format_author(comments.author),
                "comment": comments.comment,
                "contentType": comments.contentType,
                "published": comments.published.isoformat()
            }
        
        # Now format each comment (for collections)
        for comment in comments:
            comments_list.append({
                "type": "comment",
                "id": comment.id,
                "author": self.format_author(comment.author),
                "comment": comment.comment,
                "contentType": comment.contentType,
                "published": comment.published.isoformat()
            })
        
        return comments_list
        
    def format_comment_likes(self, comment):
        """Returns formatted likes for a comment."""
        return {
            "type": "likes",
            "id": f"{comment.id}/likes",
            "page": f"http://{self.request.get_host()}/social/api/authors/{comment.author.id}/commented/{comment.id}/likes",
            "page_number": 1,  # Pagination metadata
            "size": 50,  # Default page size
            "count": Like.objects.filter(object=comment.id).count(),  # Count total likes for this comment
            "src": [
                {
                    "type": "like",
                    "id": like.id,
                    "published": like.published.isoformat(),
                    "author": self.format_author(like.author),  # Format author details
                    "object": comment.id  # The comment being liked
                }
                for like in Like.objects.filter(object=comment.id).order_by("-published")[:5]  # Limit to 5 likes
            ]
        }

    def format_post(self, post, author_id):
        """Returns the formatted post object in the correct structure."""
        return {
            "type": "post",
            "id": post.id,
            "title": post.title,
            "description": post.description,
            "contentType": post.contentType,
            "content": post.content,
            "published": post.published.isoformat(),
            "visibility": post.visibility,
            "page": post.page if post.page else "",
            "author": self.format_author(post.author),  # Post author
            "comments": self.format_comments(post.comments),  #  comments
            "likes": self.format_likes(post)  # likes
        }
        
    def format_likes(self, post):
        """Returns formatted likes for a post."""
        likes_list = []
        # Get likes for this post
        post_likes = Like.objects.filter(object=post.id)
        
        for like in post_likes:
            likes_list.append({
                "type": "like",
                "id": like.id,
                "published": like.published.isoformat(),
                "author": self.format_author(like.author),
                "object": like.object,
            })
    
        return likes_list


    @method_decorator(csrf_exempt, name='dispatch')
    def post(self, request, author_id):
        """Stores any incoming request (posts, likes, comments, follows) in the inbox."""

        author_id = unquote(author_id)
        expected_author_id = f"http://{request.get_host()}/social/api/authors/{author_id}"

        print(f"Receiving new inbox item for: {expected_author_id}")
        author = get_object_or_404(Author, id=expected_author_id)
        inbox, created = Inbox.objects.get_or_create(author=author)

        data = request.data
        item_type = data.get("type").lower()
        
        if item_type == 'update':
            item_type = 'post'
        if item_type =='follow-decision':
            print("Follow-decision received in inbox")
            return JsonResponse({'status': 'ok'}, status=200)

        if self.check_disabled_nodes(data, item_type):
            # Deny any post request if its sending data from a disabled node
            return Response({"error": "Disabled Node"}, status=status.HTTP_403_FORBIDDEN)

        if item_type == "follow":
            actor_data = data.get("actor", {})
            follower_id = actor_data.get("id")
            follower_host = actor_data.get("host")

            if not follower_id:
                return Response({"error": "Missing actor id"}, status=status.HTTP_400_BAD_REQUEST)

            # Compare actor (sender) host to receiver's host
            if follower_host and follower_host.rstrip("/") != author.host.rstrip("/"):
                if follower_host[-1] != "/":
                    follower_host += "/"
            
                node, created = Node.objects.get_or_create(base_url=follower_host)
                if created:
                    print(f"Created new Node entry for host: {follower_host}")

            follower, created = Author.objects.update_or_create(
                id=follower_id,
                defaults={
                    "host": follower_host,
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


        elif item_type == "like":
            print("Received a like in the inbox")
            print(f"THIS IS THE LIKE DATA: {data}")
            like_id = data.get("id")
            like_object = data.get("object")  # The URL of the post or comment being liked
            like_author_data = data.get("author", {})
            like_author_id = like_author_data.get("id", "")
            like_published = data.get("published", timezone.now().isoformat())

            if not (like_id and like_object and like_author_id):
                return Response({"error": "Missing required like fields"}, status=status.HTTP_400_BAD_REQUEST)

            # Create or update the author (may be remote)
            author_instance, _ = Author.objects.update_or_create(
                id=like_author_id,
                defaults={
                    "host": like_author_data.get("host", ""),
                    "displayName": like_author_data.get("displayName", ""),
                    "github": like_author_data.get("github", ""),
                    "profileImage": like_author_data.get("profileImage", ""),
                    "page": like_author_data.get("page", "")
                }
            )

            like_obj = Like.objects.filter(
                author=author_instance,
                object=like_object
            ).first()

            if not like_obj:
                like_obj = Like.objects.create(
                    author=author_instance,
                    object=like_object,
                    published=like_published
                )
                inbox.inbox_likes.add(like_obj)
                print(f"[INFO] Stored Like from {like_author_id} on {like_object}")
            else:
                print("Like arlready exists")
                return Response({"error": "Follow request already exists"}, status=status.HTTP_409_CONFLICT)


        elif item_type.lower() == "comment":
            print("received comment")
            comment_id = data.get("id")
            
            comment_content = data.get("comment", "")
            comment_author_data = data.get("author", {})
            comment_author_id = comment_author_data.get("id", "")
            comment_post_id = data.get("post", "")
            print(f"THIS IS POST ID: {comment_post_id}")
            comment_published = data.get("published", timezone.now().isoformat())
            comment_content_type = data.get("contentType", "text/markdown")

            # Ensure required fields are present
            if not (comment_id and comment_author_id and comment_post_id and comment_content):
                return Response({"error": "Missing required comment fields"}, status=status.HTTP_400_BAD_REQUEST)

            # Get or create the comment author (handle remote authors)
            author_instance, _ = Author.objects.update_or_create(
                id=comment_author_id,
                defaults={
                    "host": comment_author_data.get("host", ""),
                    "displayName": comment_author_data.get("displayName", ""),
                    "github": comment_author_data.get("github", ""),
                    "profileImage": comment_author_data.get("profileImage", ""),
                    "page": comment_author_data.get("page", "")
                }
            )

            # Ensure the post exists 
            try:
                post_instance = Post.objects.get(id=comment_post_id)
            except Post.DoesNotExist:
                return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

            # Create or update the comment
            comment, _ = Comment.objects.update_or_create(
                id=comment_id,
                defaults={
                    "type": "comment",
                    "comment": comment_content,
                    "published": comment_published,
                    "author": author_instance,
                    "post": comment_post_id,
                    "contentType": comment_content_type,
                }
            )

            inbox.inbox_comments.add(comment)
            print(f"[INFO] Stored comment by {author_instance.displayName} on post {comment_post_id}")



        elif item_type.lower() == "post":
            print("Received a post in the inbox")
            
            post_id = data.get("id")
            post_title = data.get("title", "")
            post_description = data.get("description", "")
            post_content = data.get("content", "")
            post_contentType = data.get("contentType", "text/plain")
            post_visibility = data.get("visibility", "PUBLIC")
            post_published = data.get("published", timezone.now().isoformat())
            post_page = data.get("page", "")
            post_author_data = data.get("author", {})
            post_author_id = post_author_data.get("id", "")

            print("HERE0")
            print(post_id)
            
            
            #if not (post_id and post_author_id and post_title):
                #return Response({"error": "Missing required post fields"}, status=status.HTTP_400_BAD_REQUEST)

            print("HERE1")
            
            # Ensure author exists (remote or local)
            author_instance, _ = Author.objects.update_or_create(
                id=post_author_id,
                defaults={
                    "host": post_author_data.get("host", ""),
                    "displayName": post_author_data.get("displayName", ""),
                    "github": post_author_data.get("github", ""),
                    "profileImage": post_author_data.get("profileImage", ""),
                    "page": post_author_data.get("page", "")
                }
            )

            print("HERE2")
            
            # Save the post with the remote ID
            post, _ = Post.objects.update_or_create(
                id=post_id,
                defaults={
                    "title": post_title,
                    "description": post_description,
                    "content": post_content,
                    "contentType": post_contentType,
                    "visibility": post_visibility,
                    "published": post_published,
                    "author": author_instance,
                    "page": post_page or None
                }
            )
            
            print("HERE3")

            inbox.inbox_posts.add(post)
            print(f"[INFO] Stored post '{post_title}' from {post_author_id}")



        else:
            return Response({"error": "Invalid type"}, status=status.HTTP_400_BAD_REQUEST)

        inbox.save()
        print(f" Stored {item_type} in inbox.")
        return Response({"message": f"{item_type} received and stored"}, status=status.HTTP_201_CREATED)
    

    def check_disabled_nodes(self, data, item_type):
        '''
        Returns true if data is from a host on a disabled node
        '''
        author_data = {}
        # For Follow Request object, check the actor author's host
        if item_type == "Follow":
            author_data = data.get("actor", {})
        else:
            # For Post, Comment, and Like objects, check the author's host
            author_data = data.get("author", {})

        author_host = author_data.get("host")
        disabled_nodes = Node.objects.filter(enabled=False)
        # Check if actor_host matches any disabled node's base_url
        for node in disabled_nodes:
            if author_host == node.base_url:
                print('Object is from a disabled node, rejecting')
                return True
            
        return False



    def delete(self, request, author_id):
        """
        Denies a follow request by extracting the follower ID from the request body,
        updates the FollowRequest status to "denied," and removes it from the Inbox only.
        """
        author_id = unquote(author_id)
        expected_author_id = f"http://{request.get_host()}/social/api/authors/{author_id}"
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