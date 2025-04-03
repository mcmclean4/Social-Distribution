from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Author, Comment, Like, Node,Post
from .serializers import LikeSerializer
import requests 
import uuid
from datetime import datetime
import traceback
from .distribution_utils import distribute_likes, distribute_comment_likes


@api_view(['POST'])
def send_comment_like_to_inbox(request):
    """
    Receives a like request from frontend for a remote comment
    and sends it to the appropriate inbox.
    Also distributes the like to followers of the post author if it's a local post.
    """
    try:
        print("Sending Comment Like to inbox")
        # Extract data from request
        data = request.data
        print("data is:")
        print(data)
        post_fqid = data.get('postFqid', '')
        author_fqid = data.get('authorFqid', '')
        comment_fqid = data.get('commentFqid', '')
        
        if not all([post_fqid, author_fqid, comment_fqid]):
            return Response(
                {"error": "Missing required information"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the current user's author profile
        liker = Author.objects.get(user=request.user)
        
        # Try to get the comment from our database (it might be cached)
        uuid_part = comment_fqid.split('/')[-1]
        existing_comment = Comment.objects.filter(id__endswith=uuid_part).first()
        
        if not existing_comment:
            print('failed to get existing comment')
            # Create a placeholder for the comment
            # Extract post and author info from the IDs
            if '/authors/' in post_fqid and '/posts/' in post_fqid:
                parts = post_fqid.split('/authors/')
                host = parts[0]
                remainder = parts[1]
                post_author_id = remainder.split('/posts/')[0]
                
                try:
                    # Try to find the remote author in our database
                    remote_author = Author.objects.get(id__endswith=post_author_id)
                except Author.DoesNotExist:
                    # Create a placeholder remote author
                    remote_author = Author.objects.create(
                        id=f"{host}/authors/{post_author_id}",
                        host=host,
                        displayName="Remote Author",
                        page=f"{host}/authors/{post_author_id}"
                    )
                
                # Create a placeholder comment
                existing_comment = Comment(
                    id=comment_fqid,
                    author=remote_author,
                    post=post_fqid,
                    comment="Remote Comment",
                    contentType="text/markdown",
                    published=datetime.now()
                )
                existing_comment.save()
            else:
                return Response(
                    {"error": "Invalid post or comment ID format"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get or extract the post author's ID
        post_author_id = None
        # First try to get from the post if it exists locally
        try:
            post = Post.objects.get(id=post_fqid)
            post_author_id = post.author.id
            post_author_host = post.author.host
            print(f"Found a post, author ID: {post_author_id}")
        except Post.DoesNotExist:
            # Extract from the post_fqid
            if '/authors/' in post_fqid and '/posts/' in post_fqid:
                parts = post_fqid.split('/authors/')
                host = parts[0]
                remainder = parts[1]
                author_id_part = remainder.split('/posts/')[0]
                post_author_id = f"{host}/authors/{author_id_part}"
                print(f"Extracted post author ID: {post_author_id}")
        
        # Comment already exists (should always happen)
        # Check if the like already exists
        existing_like = Like.objects.filter(
            author=liker,
            object=existing_comment.id
        ).first()
        
        new_like = None
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
                object=existing_comment.id
            )
            action = 'liked'
            # Update like count
            like_count = Like.objects.filter(object=existing_comment.id).count()
            print(f"From comment_like_views: Updated like count: {like_count}")
            
            # Determine if this is a local or remote post/comment
            is_local_post = False
            current_host = request.get_host()
            
            if post_fqid.startswith(f"http://{current_host}") or post_fqid.startswith(f"https://{current_host}"):
                is_local_post = True
                print(f"From comment_like_views: This is a local post: {post_fqid}")
            else:
                print(f"From comment_like_views: This is a remote post: {post_fqid}")
            
            # Send to the comment author's inbox
            try:
                # Extract host and author ID from the comment
                comment_author = Author.objects.get(id=existing_comment.author.id)
                host = post_author_host
                
                # Get the foreign node information
                node = Node.objects.get(base_url__contains=host.split('//')[1])
                
                # Construct inbox URL
                inbox_url = f"{post_author_id}/inbox"
                
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
                    "object": existing_comment.id,
                    "summary": f"{liker.displayName} liked your comment"
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
                    print(f"Error sending comment like to inbox: {response.status_code} - {response.text}")
                
            except Node.DoesNotExist:
                print(f"From comment_like_views: Node does not exist for host: {host}")
            except Exception as e:
                print(f"From comment_like_views: Failed to send comment like to inbox: {str(e)}")
            
            # If it's a local post, distribute the like to the post author's followers
            if is_local_post and new_like and post_author_id:
                try:
                    # Create the like data structure for distribution
                    distribute_like_data = {
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
                        "object": existing_comment.id,
                        "summary": f"{liker.displayName} liked a comment on a post by {existing_comment.author.displayName}"
                    }
                    
                    # Distribute the like to followers of the post author
                    distribute_comment_likes(new_like, distribute_like_data, post_author_id)
                    print(f"From comment_like_views: Distributed comment like to followers of post author: {post_author_id}")
                except Exception as e:
                    print(f"From comment_like_views: Error distributing comment like to followers: {str(e)}")
                    print(traceback.format_exc())
        
        # Update like count
        like_count = Like.objects.filter(object=existing_comment.id).count()
        
        # Return a standardized response
        return Response({
            "status": "success",
            "action": action,
            "like_count": like_count
        })
        
    except Author.DoesNotExist:
        return Response(
            {"error": "From comment_like_views: Author not found for current user"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        import traceback
        print(f"From comment_like_views: Exception in send_comment_like_to_inbox: {str(e)}")
        print(traceback.format_exc())
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )   


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
            return Response({"error": "From comment_like_views: Comment not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all likes for this comment
        likes = Like.objects.filter(object=comment.id).order_by("published")
        
        # Serialize the likes
        like_serializer = LikeSerializer(likes, many=True)
        
        # Return the likes object as specified in the API
        return Response({
            "type": "likes",
            "id": f"http://{request.get_host()}/social/api/authors/{author_id}/posts/{post_serial}/commented/{comment_fqid}/likes",
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
