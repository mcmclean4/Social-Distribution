from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Author, Like, Post
from .serializers import LikeSerializer

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

@api_view(['GET'])
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
            "type": "liked",
            "items": serializer.data
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