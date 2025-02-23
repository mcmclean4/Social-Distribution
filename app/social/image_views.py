from rest_framework.decorators import api_view
from .models import Post, Author
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, JsonResponse
import mimetypes
from .models import Post


@api_view(['GET'])
def getImage(request, internal_id):
    print(request)
    print(internal_id)
    post = get_object_or_404(Post, internal_id=internal_id)

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

    #return Response(status=200)
    return FileResponse(open(image_path, 'rb'), content_type=mime_type)

