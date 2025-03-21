from rest_framework.decorators import api_view
from .models import Post, Author
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, JsonResponse, HttpResponse
import mimetypes
from .models import Post
from urllib.parse import unquote
import base64


@api_view(['GET'])
def get_image_with_serial(request, author_serial, post_serial):
    '''
    Returns a post's image as binary given the author and post serial numbers
    '''

    node_name = "http://localhost:8000/"
    post_fqid = f"{node_name}social/api/authors/{author_serial}/posts/{post_serial}"
    post = get_object_or_404(Post, id=post_fqid)

    return serve_post_image(post)


@api_view(['GET'])
def get_image_with_fqid(request, post_fqid):
    '''
    Returns a post's image as binary given the post's fqid (assuming percent encoded)
    '''
    
    post_fqid = unquote(post_fqid)
    post = get_object_or_404(Post, id=post_fqid)

    return serve_post_image(post)


def serve_post_image(post):
    """
    Helper function to serve an image from a Post object where content is stored as base64.
    Returns the decoded binary image data.
    """
    # Check if the post has content
    if not post.content:
        return JsonResponse({"error": "Image not found"}, status=404)
    
    # Check if the post's contentType is an image type
    if not post.contentType.startswith('image/') and post.contentType != 'application/base64':
        return JsonResponse({"error": "File is not a valid image"}, status=404)
    
    try:
        # Decode the base64 content back to binary
        image_data = base64.b64decode(post.content)
        
        # Determine the MIME type from the contentType field
        if post.contentType == 'image/png;base64':
            mime_type = 'image/png'
        elif post.contentType == 'image/jpeg;base64':
            mime_type = 'image/jpeg'
        else:
            # Default for application/base64
            mime_type = 'application/octet-stream'
        
        # Create a response with the binary image data
        response = HttpResponse(image_data, content_type=mime_type)
        return response
    
    except base64.binascii.Error:
        return JsonResponse({"error": "Invalid base64 data"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Error processing image: {str(e)}"}, status=500)
