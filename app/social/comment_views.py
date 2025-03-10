from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Post, Author, Comment
from .serializers import CommentSerializer
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from django.http import Http404

@api_view(['GET', 'POST'])
def get_post_comments(request, author_id, post_serial):
    """
    Get all comments for a specific post or add a new comment
    """
    try:
        # Construct the full post ID URL

        #post_id = f"http://{request.get_host()}/social/api/authors/{author_id}/posts/{post_serial}"
        post_id = f"http://localhost:8000/social/api/authors/{author_id}/posts/{post_serial}"
        print("Post id is,", post_id)
        post = Post.objects.get(id=post_id)
        
        if request.method == 'GET':
            # Get all comments for this post
            comments = Comment.objects.filter(post=post_id)
            
            # Serialize the comments
            serializer = CommentSerializer(comments, many=True)
            
            # Return the comments object as specified in the API
            return Response({
                "type": "comments",
                "page": 1,
                "size": len(comments),
                "post": post_id,
                "id": f"http://{request.get_host()}/social/api/authors/{author_id}/posts/{post_serial}/comments",
                "comments": serializer.data
            })
        
        elif request.method == 'POST':
            # Handle adding a new comment
            author_data = request.data.get('author', {})
            author_id_val = author_data.get('id')
            
            if not author_id_val:
                return Response({"error": "Author ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Try to get the author, or create a new one if it's a remote author
            try:
                author = Author.objects.get(id=author_id_val)
            except Author.DoesNotExist:
                # For remote authors, might want to create a placeholder
                author = Author.objects.create(**author_data)
            
            # Create a new comment
            comment_data = {
                'type': 'comment',
                'author': author,
                'comment': request.data.get('comment', ''),
                'contentType': request.data.get('contentType', 'text/markdown'),
                'post': post_id,
                # The ID will be generated automatically in the model's save method
            }
            
            comment = Comment.objects.create(**comment_data)
            
            # Return the serialized comment
            serializer = CommentSerializer(comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
@api_view(['GET'])
def get_comments_by_post_fqid(request, post_fqid):
    """
    Get all comments for a post by its fully qualified ID
    """
    try:
        # The post_fqid is the full URL of the post
        post = Post.objects.get(id=post_fqid)
        
        # Get all comments for this post
        comments = Comment.objects.filter(post=post_fqid)
        
        # Serialize the comments
        serializer = CommentSerializer(comments, many=True)
        
        # Return the comments object
        return Response({
            "type": "comments",
            "page": 1,
            "size": len(comments),
            "post": post_fqid,
            "id": f"http://{request.get_host()}/social/api/posts/{post_fqid}/comments",
            "comments": serializer.data
        })
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_specific_comment(request, author_id, post_serial, remote_comment_fqid):
    """
    Get a specific comment by its fully qualified ID
    """
    try:
        # URL decode the comment ID if necessary
        # from urllib.parse import unquote
        # comment_id = unquote(remote_comment_fqid)
        
        # Get the comment by its ID
        comment = Comment.objects.get(id=remote_comment_fqid)
        
        # Serialize the comment
        serializer = CommentSerializer(comment)
        
        # Return the comment
        return Response(serializer.data)
    except Comment.DoesNotExist:
        return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def add_comment(request, author_id, post_id):
    """
    Add a comment to a post
    """
    try:
        # Construct the full post ID
        print(request.get_host())
        post_url = f"http://{request.get_host()}/social/api/authors/{author_id}/posts/{post_id}"
        
        # Check if the post exists
        post = Post.objects.get(id=post_url)
        
        # Check if the author exists
        author_data = request.data.get('author', {})
        author_id = author_data.get('id')
        
        if not author_id:
            return Response({"error": "Author ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to get the author, or create a new one if it's a remote author
        try:
            author = Author.objects.get(id=author_id)
        except Author.DoesNotExist:
            # For remote authors, might want to create a placeholder
            author = Author.objects.create(**author_data)
        
        # Create a new comment
        comment_data = {
            'type': 'comment',
            'author': author,
            'comment': request.data.get('comment', ''),
            'contentType': request.data.get('contentType', 'text/markdown'),
            'post': post_url,
            # The ID will be generated automatically in the model's save method
        }
        
        comment = Comment.objects.create(**comment_data)
        
        # Return the serialized comment
        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Post.DoesNotExist:
        return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Optional: Comment Like View
class CommentLikeView(APIView):
    """
    API view for liking comments
    """
    def post(self, request, author_id, post_id, comment_id, format=None):
        try:
            # Get the comment
            comment = Comment.objects.get(id=comment_id)
            
            # Get the author who is liking the comment
            liker = Author.objects.get(user=request.user)
            
            return Response({"status": "Comment liked"}, status=status.HTTP_200_OK)
        except Comment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Author.DoesNotExist:
            return Response({"error": "Author not found"}, status=status.HTTP_404_NOT_FOUND)
        

@api_view(['GET', 'POST'])
def get_author_comments(request, author_id):
    """
    GET: Get all comments made by an author
    POST: Add a new comment to a post
    """
    # Construct the author URL
    author_url = f"http://{request.get_host()}/social/api/authors/{author_id}"
    
    try:
        # Find the author
        author = Author.objects.get(id=author_url)
        
        if request.method == 'GET':
            # Get all comments by this author
            comments = Comment.objects.filter(author=author)
            
            # Serialize the comments
            serializer = CommentSerializer(comments, many=True)
            
            # Return the comments
            return Response(serializer.data)
            
        elif request.method == 'POST':
            # Check if the request data is a comment
            if request.data.get('type') != 'comment':
                return Response({"error": "Object type must be 'comment'"}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            # Get the post ID from the request
            post_url = request.data.get('post')
            if not post_url:
                return Response({"error": "Post ID is required"}, 
                               status=status.HTTP_400_BAD_REQUEST)
            
            # Create the comment
            data = {
                'author': author,
                'comment': request.data.get('comment', ''),
                'contentType': request.data.get('contentType', 'text/markdown'),
                'post': post_url
            }
            
            comment = Comment.objects.create(**data)
            
            # Serialize and return the created comment
            serializer = CommentSerializer(comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
    except Author.DoesNotExist:
        return Response({"error": "Author not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_author_comments_by_fqid(request, author_fqid):
    """
    Get all comments made by an author (using fully qualified ID)
    """
    try:
        # Find the author by FQID
        author = Author.objects.get(id=author_fqid)
        
        # Get all comments by this author
        comments = Comment.objects.filter(author=author)
        
        # Serialize the comments
        serializer = CommentSerializer(comments, many=True)
        
        # Return the comments
        return Response(serializer.data)
        
    except Author.DoesNotExist:
        return Response({"error": "Author not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_specific_comment_by_serial(request, author_id, comment_serial):
    """
    Get a specific comment by its serial number
    """
    try:
        # Print debug information
        print(f"Looking for comment: author_id={author_id}, comment_serial={comment_serial}")
        
        # Try multiple formats to find the comment
        possible_ids = [
            f"http://{request.get_host()}/api/authors/{author_id}/commented/{comment_serial}",
            f"http://localhost:8000/api/authors/{author_id}/commented/{comment_serial}"
        ]
        
        # Try finding the comment by the full IDs
        comment = None
        for possible_id in possible_ids:
            print(f"Trying ID: {possible_id}")
            try:
                comment = Comment.objects.get(id=possible_id)
                print(f"Found comment with ID: {possible_id}")
                break
            except Comment.DoesNotExist:
                continue
        
        # If still not found, try by just the UUID part
        if not comment:
            print(f"Trying to find by UUID part: {comment_serial}")
            comments = Comment.objects.filter(id__endswith=comment_serial)
            
            if comments.exists():
                comment = comments.first()
                print(f"Found comment with ID ending with: {comment_serial}")
            else:
                # Print all comment IDs for debugging
                all_comments = Comment.objects.all()
                print("All comment IDs in database:")
                for c in all_comments:
                    print(f"  - {c.id}")
                    
                return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Serialize and return the comment
        serializer = CommentSerializer(comment)
        return Response(serializer.data)
        
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_comment_by_fqid(request, comment_fqid):
    """
    Get a specific comment by its fully qualified ID
    """
    try:
        # Find the comment by its FQID
        comment = Comment.objects.get(id=comment_fqid)
        
        # Serialize and return the comment
        serializer = CommentSerializer(comment)
        return Response(serializer.data)
        
    except Comment.DoesNotExist:
        return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)