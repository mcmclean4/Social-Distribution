from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Author, Comment, Like, Node
from .serializers import LikeSerializer
import requests 

@api_view(['GET'])
def get_comment_likes(request, author_id, post_serial, comment_fqid):
    """
    Get all likes for a specific comment
    """
    try:
        # Find the comment by its fully qualified ID
        uuid_part = comment_fqid.split('/')[-1]
        comment = Comment.objects.filter(id__endswith=uuid_part).first()
        
        if not comment:
            return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all likes for this comment
        likes = Like.objects.filter(object=comment.id).order_by("published")
        
        # Serialize the likes
        like_serializer = LikeSerializer(likes, many=True)
        
        # Return the likes object as specified in the API
        return Response({
            "type": "likes",
            "id": f"http://{request.get_host()}/social/api/authors/{author_id}/posts/{post_serial}/comments/{comment_fqid}/likes",
            "page": f"http://{request.get_host()}/social/authors/{author_id}/posts/{post_serial}/comments/{comment_fqid}/likes",
            "page_number": 1,
            "size": 50,
            "count": likes.count(),
            "src": like_serializer.data
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def like_comment(request, author_id, post_id, comment_fqid):
    """
    Like a comment
    """
    print(f"like_comment called with author_id={author_id}, post_id={post_id}, comment_id={comment_fqid}")
    
    try:
        # Try to match by UUID part only
        uuid_part = comment_fqid.split('/')[-1] 
        print(f"Looking for comment with UUID part: {uuid_part}")
        
        # Try direct lookup first
        comment = None
        try:
            comment = Comment.objects.get(id__endswith=uuid_part)
            print(f"Found comment directly: {comment.id}")
        except Comment.DoesNotExist:
            # Try more flexible lookup
            comments = Comment.objects.filter(id__contains=uuid_part)
            if comments.exists():
                comment = comments.first()
                print(f"Found comment with contains: {comment.id}")
            else:
                print(f"No comment found containing: {uuid_part}")
                # Check all comment IDs to help debug
                all_comments = Comment.objects.all()
                print(f"All comment IDs in database:")
                for c in all_comments:
                    print(f"  - {c.id}")
                return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get the current user's author profile
        liker = Author.objects.get(user=request.user)
        print(f"Liker author: {liker.id}")
        
        # Check if the like already exists
        existing_like = Like.objects.filter(
            author=liker,
            object=comment.id
        ).first()
        
        if existing_like:
            # Unlike if already liked
            print(f"Removing existing like: {existing_like.id}")
            existing_like.delete()
            action = 'unliked'
        else:
            # Create a new like
            print(f"Creating new like for comment: {comment.id}")
            new_like = Like.objects.create(
                type="like",
                author=liker,
                object=comment.id
            )
            action = 'liked'
            like_to_inbox(comment, new_like)
        
        # Update like count
        like_count = Like.objects.filter(object=comment.id).count()
        print(f"Updated like count: {like_count}")
        
        # Return a standardized response
        response_data = {
            "status": "success",
            "action": action,
            "like_count": like_count
        }
        print(f"Returning response: {response_data}")
        return Response(response_data)
            
    except Author.DoesNotExist:
        print("Author not found for current user")
        return Response({"error": "Author not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        # Log the error for debugging
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error liking comment: {str(e)}")
        print(f"Exception occurred: {str(e)}")
        print(traceback.format_exc())
        
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
def like_to_inbox(comment, like):
    '''
    Sends a Like object to the post author's inbox
    '''
    try:
        author_serial = comment.author.id.split('/')[-1]
        post_node = Node.objects.get(base_url=comment.author.host)
        # Change to use post.author.id instead of author_serial if it turns out inbox should actually use fqid
        inbox_url = f"{post_node.base_url}authors/{author_serial}/inbox"
        print(inbox_url)

        # Create the like object according to the example format
        like_data = {
            "type": "like",
            "author": {
                "type": "author",
                "id": comment.author.id,
                "host": comment.author.host,
                "displayName": comment.author.displayName,
                "page": comment.author.page,
                "github": comment.author.github,
                "profileImage": comment.author.profileImage
            },
            "published": like.published.isoformat(),
            "id": like.id,
            "object": comment.id
        }

        # Send the post to the recipient's inbox
        response = requests.post(
            inbox_url,
            json=like_data,
            auth=(post_node.auth_username, post_node.auth_password),
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        response.raise_for_status()
        print(f"Successfully sent like to {comment.author.id}")

    except Node.DoesNotExist:
        print(f"Node does not exist for host: {comment.author.host}. May have been removed.")
        pass
    except Exception as e:
        print(f"Failed to send like to {comment.author.id}: {str(e)}")
        pass
