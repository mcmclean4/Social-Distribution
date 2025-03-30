from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response
from .models import Author, Like, Post, Node
from .serializers import LikeSerializer
from .authentication import NodeBasicAuthentication
import requests
import uuid
from datetime import datetime
import json

@api_view(['GET'])
def get_liked_by_author(request, author_id):
    """
    Get all things liked by an author
    """
    try:
        # Find the author 
        author_url = f"http://{request.get_host()}/social/api/authors/{author_id}"
        author = Author.objects.get(id=author_url)
        
        # Get all likes by this author
        likes = Like.objects.filter(author=author)
        
        # Serialize the likes
        serializer = LikeSerializer(likes, many=True)
        
        # Return the likes object
        return Response({
            "type": "liked",
            "items": serializer.data
        })
    except Author.DoesNotExist:
        return Response({"error": "Author not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_single_like(request, author_id, like_serial):
    """
    Get a single like by an author
    """
    try:
        # Construct the like ID
        like_id = f"http://{request.get_host()}/social/api/authors/{author_id}/liked/{like_serial}"
        
        # Get the like
        like = Like.objects.get(id=like_id)
        
        # Serialize the like
        serializer = LikeSerializer(like)
        
        # Return the like object
        return Response(serializer.data)
    except Like.DoesNotExist:
        return Response({"error": "Like not found"}, status=status.HTTP_404_NOT_FOUND)



@api_view(['POST'])
def send_like_to_inbox(request):
    """
    Receives a like request from frontend for a remote post
    and sends it to the appropriate inbox
    """
    try:
        print("Sending Like to inbox")
        # Extract data from request
        data = request.data
        post_fqid = data.get('postFqid', '')
        author_fqid = data.get('authorFqid', '')
        
        if not post_fqid or not author_fqid:
            return Response(
                {"error": "Missing post or author information"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the current user's author profile
        liker = Author.objects.get(user=request.user)
        
        # Try to find the post in our database (might have been cached)
        try:
            print("likee")
            post = Post.objects.get(id=post_fqid)
        except Post.DoesNotExist:
            # Create a placeholder post entry for the remote post
            # Extract author info from the post ID or from the provided author_fqid
            if '/authors/' in post_fqid and '/posts/' in post_fqid:
                parts = post_fqid.split('/authors/')
                host = parts[0]
                remainder = parts[1]
                author_id_part = remainder.split('/posts/')[0]
                post_id_part = remainder.split('/posts/')[1]
                
                # Get or create a placeholder for the remote author
                remote_author, _ = Author.objects.get_or_create(
                    id=f"{host}/authors/{author_id_part}",
                    defaults={
                        'host': host,
                        'displayName': 'Remote Author',
                        'page': f"{host}/authors/{author_id_part}"
                    }
                )
                
                # Create a placeholder for the remote post
                post = Post(
                    id=post_fqid,
                    author=remote_author,
                    published=datetime.now(),
                    title="Remote Post"
                )
                post.save()
            else:
                return Response(
                    {"error": "Invalid post ID format"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Check if the like already exists
        existing_like = Like.objects.filter(
            author=liker,
            object=post.id
        ).first()
        
        if existing_like:
            # Unlike if already liked
            existing_like.delete()
            action = 'unliked'
            # Unlike is typically not sent to inbox
            
        else:
            # Create a new like
            new_like = Like.objects.create(
                type="like",
                author=liker,
                object=post.id
            )
            action = 'liked'
            
            # Send to inbox
            try:
                # Extract host and author ID from the post ID
                post_parts = post.id.split('/authors/')
                host = post_parts[0] 
                remaining = post_parts[1]
                remote_author_id = remaining.split('/posts/')[0]
                
                # Get the foreign node information
                node = Node.objects.get(base_url__contains=host.split('//')[1])
                
                # Construct inbox URL
                inbox_url = f"{node.base_url}authors/{remote_author_id}/inbox"
                
                # Create like data
                like_data = {
                    "type": "like",
                    "author": {
                        "type": "author",
                        "id": liker.id,
                        "host": liker.host,
                        "displayName": liker.displayName,
                        "page": liker.page,
                        "github": liker.github,
                        "profileImage": liker.profileImage
                    },
                    "published": new_like.published.isoformat(),
                    "id": new_like.id,
                    "object": post.id,
                    "summary": f"{liker.displayName} liked your post"
                }
                
                # Send to inbox
                response = requests.post(
                    inbox_url,
                    json=like_data,
                    auth=(node.auth_username, node.auth_password),
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                
                if response.status_code >= 400:
                    print(f"Error sending like to inbox: {response.status_code} - {response.text}")
                
            except Node.DoesNotExist:
                print(f"Node does not exist for host: {host}")
            except Exception as e:
                print(f"Failed to send like to inbox: {str(e)}")
        
        # Update like count
        like_count = Like.objects.filter(object=post.id).count()
        
        # Return a standardized response
        return Response({
            "status": "success",
            "action": action,
            "like_count": like_count
        })
        
    except Author.DoesNotExist:
        return Response(
            {"error": "Author not found for current user"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        import traceback
        print(f"Exception in send_like_to_inbox: {str(e)}")
        print(traceback.format_exc())
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@authentication_classes([NodeBasicAuthentication])
def get_liked_by_author_fqid(request, author_fqid):
    """
    Get all things liked by an author using FQID
    """
    try:
        # Find the author by FQID
        author = Author.objects.get(id=author_fqid)
        
        # Get all likes by this author
        likes = Like.objects.filter(author=author)
        
        # Serialize the likes
        serializer = LikeSerializer(likes, many=True)
        
        # Return the likes object
        return Response({
            "type": "likes",
            "page": author.page,
            "id": author.id,
            "page_number": 1,
            "count": len(likes),
            "src": serializer.data
        })
    except Author.DoesNotExist:
        return Response({"error": "Author not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_like_by_fqid(request, like_fqid):
    """
    Get a single like by its FQID
    """
    try:
        # Get the like by FQID
        like = Like.objects.get(id=like_fqid)
        
        # Serialize the like
        serializer = LikeSerializer(like)
        
        # Return the like object
        return Response(serializer.data)
    except Like.DoesNotExist:
        return Response({"error": "Like not found"}, status=status.HTTP_404_NOT_FOUND)
    
@api_view(['GET'])
def get_post_likes(request, author_id, post_id):
    """
    Get all likes for a specific post
    """
    try:
        # Construct the full post ID URL
        post_url = f"http://{request.get_host()}/social/api/authors/{author_id}/posts/{post_id}"
        
        # Find the post by its ID
        post = Post.objects.get(id=post_url)
        
        # Get all likes for this post
        likes = Like.objects.filter(object=post_url).order_by("published")
        
        # Serialize the likes
        like_serializer = LikeSerializer(likes, many=True)
        
        # Return the likes object as specified in the API
        return Response({
            "type": "likes",
            "id": f"{post_url}/likes",
            "page": f"{post.page}/likes" if post.page else None,
            "page_number": 1,
            "size": 50,
            "count": likes.count(),
            "src": like_serializer.data
        })
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_post_likes_by_fqid(request, post_fqid):
    """
    Get all likes for a specific post using the post's fqid
    """
    try:
        # Find the post by its ID
        post = Post.objects.get(id=post_fqid)
        
        # Get all likes for this post
        likes = Like.objects.filter(object=post_fqid).order_by("published")
        
        # Serialize the likes
        like_serializer = LikeSerializer(likes, many=True)
        
        # Return the likes object as specified in the API
        return Response({
            "type": "likes",
            "id": f"{post_fqid}/likes",
            "page": f"{post.page}/likes" if post.page else None,
            "page_number": 1,
            "size": 50,
            "count": likes.count(),
            "src": like_serializer.data
        })
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['GET'])
def get_liked_by_post_fqid(request, post_fqid):
    """
    Checks if the request's user has liked the post
    """
    try:
        request_user_author = request.user.author
        #author_serial = request_user_author.id.split('/')[-1]
        node = Node.objects.get(base_url=request_user_author.host)
        # Change to use post.author.id instead of author_serial if it turns out inbox should actually use fqid
        liked_url = f"{node.base_url}authors/{request_user_author.id}/liked/"
        print("LIKED URL:")
        print(liked_url )

        # Send the post to the recipient's inbox
        response = requests.get(
            liked_url,
            auth=(node.auth_username, node.auth_password),
            headers={"Accept": "application/json"},
            timeout=5
        )
        response.raise_for_status()
        likes = response.json()
        for like in likes['src']:
            print(like['object'])
            if like['object'] == post_fqid:
                return Response(like)
            
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)


    except Node.DoesNotExist:
        print(f"Node does not exist for host: {request_user_author.host}. May have been removed.")
        pass
    except Exception as e:
        print(f"Failed to get liked for {request_user_author.id}: {str(e)}")
        pass
