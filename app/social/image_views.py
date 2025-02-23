from rest_framework.decorators import api_view
from .models import Post, Author
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, JsonResponse
import mimetypes
from .models import Post
from urllib.parse import unquote


@api_view(['GET'])
def getImageWithSerial(request, author_serial, post_serial):
    '''
    Returns a post's image as binary given the author and post serial numbers
    '''

    node_name = "http://localhost:8000/"
    post_fqid = f"{node_name}social/api/authors/{author_serial}/posts/{post_serial}"
    post = get_object_or_404(Post, id=post_fqid)

    return serve_post_image(post)


@api_view(['GET'])
def getImageWithFQID(request, post_fqid):
    '''
    Returns a post's image as binary given the post's fqid (assuming percent encoded)
    '''
    
    post_fqid = unquote(post_fqid)
    post = get_object_or_404(Post, id=post_fqid)

    return serve_post_image(post)


def serve_post_image(post):
    """
    Helper function to serve an image from a Post object.
    """

    # Check if the post has an image
    if not post.image:
        return JsonResponse({"error": "Image not found"}, status=404)
    print(post.image)

    # Get the image file path
    image_path = post.image.path

    # Determine the MIME type (default to application/octet-stream if unknown)
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        return JsonResponse({"error": "File is not a valid image"}, status=404)

    return FileResponse(open(image_path, 'rb'), content_type=mime_type)
