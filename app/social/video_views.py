from rest_framework.decorators import api_view
from .models import Post, Author
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from urllib.parse import unquote
import base64

@api_view(['GET'])
def get_video_with_serial(request, author_serial, post_serial):
    '''
    Returns a post's video as binary given the author and post serial numbers
    '''
    node_name = "http://localhost:8000/"
    post_fqid = f"{node_name}social/api/authors/{author_serial}/posts/{post_serial}"
    post = get_object_or_404(Post, id=post_fqid)

    return serve_post_video(post)

@api_view(['GET'])
def get_video_with_fqid(request, post_fqid):
    """
    Returns a post's video as binary given the post's fqid
    """
    import sys
    sys.stdout.write(f"\n===== get_video_with_fqid CALLED =====\n")
    sys.stdout.write(f"Raw post_fqid: {post_fqid}\n")
    sys.stdout.flush()

    # First, URL decode the FQID
    decoded_fqid = unquote(post_fqid)
    sys.stdout.write(f"Decoded post_fqid: {decoded_fqid}\n")
    sys.stdout.flush()

    try:
        # Method 1: Try direct lookup by ID
        try:
            post = Post.objects.get(id=decoded_fqid)
            sys.stdout.write(f"Found post by exact ID match: {post.title}\n")
            sys.stdout.flush()
        except Post.DoesNotExist:
            sys.stdout.write(f"Post not found by exact ID, trying alternatives...\n")
            sys.stdout.flush()

            # Method 2: Try extracting the internal_id
            try:
                parts = decoded_fqid.split("/posts/")
                if len(parts) > 1:
                    internal_id = parts[1]
                    sys.stdout.write(f"Extracted internal_id: {internal_id}\n")
                    sys.stdout.flush()

                    post = Post.objects.get(internal_id=internal_id)
                    sys.stdout.write(f"Found post by internal_id: {post.title}\n")
                    sys.stdout.flush()
                else:
                    raise Post.DoesNotExist("Could not extract internal_id")
            except (Post.DoesNotExist, IndexError, ValueError) as e:
                sys.stdout.write(f"Error finding post by internal_id: {str(e)}\n")
                sys.stdout.flush()

                # Method 3: List all posts and look for similar IDs
                sys.stdout.write("Listing all posts to find match:\n")
                posts = Post.objects.all()
                for p in posts:
                    sys.stdout.write(f"Post ID: {p.id}, internal_id: {p.internal_id}, title: {p.title}\n")

                    # Check if this post's ID contains the post_fqid
                    if str(p.internal_id) in decoded_fqid:
                        sys.stdout.write(f"Found potential match by internal_id in string: {p.title}\n")
                        post = p
                        break
                else:
                    return HttpResponse("Post not found after all attempts", status=404)

        # Ensure it's a video post
        if not post.contentType.startswith('video/'):
            sys.stdout.write(f"Found post is not a video: {post.contentType}\n")
            sys.stdout.flush()
            return HttpResponse("Not a video post", status=400)

        # Serve the video
        try:
            video_data = base64.b64decode(post.content)
            sys.stdout.write(f"Successfully decoded {len(video_data)} bytes of video data\n")
            sys.stdout.flush()

            # Determine content type
            if post.contentType == 'video/mp4;base64':
                mime_type = 'video/mp4'
            elif post.contentType == 'video/webm;base64':
                mime_type = 'video/webm'
            else:
                mime_type = 'video/mp4'  # Default

            sys.stdout.write(f"Serving video with MIME type: {mime_type}\n")
            sys.stdout.flush()

            # Create and return the response
            response = HttpResponse(video_data, content_type=mime_type)
            return response

        except Exception as e:
            sys.stdout.write(f"Error serving video: {str(e)}\n")
            sys.stdout.flush()
            return HttpResponse(f"Error serving video: {str(e)}", status=500)

    except Exception as e:
        import traceback
        sys.stdout.write(f"Unexpected error: {str(e)}\n")
        sys.stdout.write(traceback.format_exc())
        sys.stdout.flush()
        return HttpResponse(f"Error: {str(e)}", status=500)

def serve_post_video(post):
    """
    Helper function to serve a video from a Post object where content is stored as base64.
    Returns the decoded binary video data.
    """
    # Check if the post has content
    if not post.content:
        return JsonResponse({"error": "Video not found"}, status=404)

    # Check if the post's contentType is a video type
    if not post.contentType.startswith('video/'):
        return JsonResponse({"error": "File is not a valid video"}, status=404)

    try:
        # Decode the base64 content back to binary
        video_data = base64.b64decode(post.content)

        # Determine the MIME type from the contentType field
        if post.contentType == 'video/mp4;base64':
            mime_type = 'video/mp4'
        elif post.contentType == 'video/webm;base64':
            mime_type = 'video/webm'
        else:
            # Default
            mime_type = 'video/mp4'

        # Create a response with the binary video data
        response = HttpResponse(video_data, content_type=mime_type)
        return response

    except base64.binascii.Error:
        return JsonResponse({"error": "Invalid base64 data"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Error processing video: {str(e)}"}, status=500)
@api_view(['GET'])
def debug_image_url(request, post_id):
    """Debug view to check image URL formats"""
    print(f"\n=== DEBUG: Checking image URL for post {post_id} ===", flush=True)

    # Construct the full URL for the post
    post_url = f"http://localhost:8000/social/api/authors/2/posts/{post_id}"
    encoded_url = post_url.replace(':', '%3A').replace('/', '%2F')

    image_url = f"/social/api/posts/{encoded_url}/image"
    video_url = f"/social/api/posts/{encoded_url}/video"

    print(f"Image URL: {image_url}", flush=True)
    print(f"Video URL: {video_url}", flush=True)

    # Try to find the post in the database
    try:
        post = Post.objects.get(id=post_url)
        print(f"Post found with ID: {post_url}", flush=True)
        print(f"Title: {post.title}", flush=True)
        print(f"Content Type: {post.contentType}", flush=True)
        return HttpResponse(f"""
        <h1>Post Found: {post.title}</h1>
        <p>Content Type: {post.contentType}</p>
        <p>Image URL: <a href="{image_url}">{image_url}</a></p>
        <p>Video URL: <a href="{video_url}">{video_url}</a></p>
        """)
    except Post.DoesNotExist:
        print(f"No post found with ID: {post_url}", flush=True)
        return HttpResponse(f"No post found with ID: {post_url}", status=404)

@api_view(['GET'])
def debug_video_url(request):
    """Debug function to see what URL Django is seeing"""
    path = request.path
    print(f"Path: {path}")

    if '/video' in path:
        # Extract the post_fqid part
        post_fqid = path.split('/video')[0].split('/posts/')[1]
        print(f"Extracted post_fqid: {post_fqid}")

        try:
            decoded_fqid = unquote(post_fqid)
            print(f"Decoded post_fqid: {decoded_fqid}")

            post = Post.objects.get(id=decoded_fqid)
            print(f"Found post: {post.title}")

            return HttpResponse(f"Found post: {post.title}, Content Type: {post.contentType}")
        except Post.DoesNotExist:
            print(f"No post found with ID: {decoded_fqid}")
            return HttpResponse(f"No post found with ID: {decoded_fqid}", status=404)

    return HttpResponse(f"Path does not contain '/video': {path}", status=400)    

def test_video(request, post_id):
    """Simple test function to serve a video"""
    import sys
    sys.stdout.write(f"\n===== TEST VIDEO CALLED =====\n")
    sys.stdout.write(f"Post ID: {post_id}\n")
    sys.stdout.flush()

    from .models import Post
    import base64

    try:
        post = Post.objects.get(internal_id=post_id)
        sys.stdout.write(f"Found post: {post.title}, content type: {post.contentType}\n")
        sys.stdout.flush()

        if not post.contentType.startswith('video/'):
            sys.stdout.write(f"Not a video post. Content type: {post.contentType}\n")
            sys.stdout.flush()
            return HttpResponse("Not a video post", status=400)

        try:
            video_data = base64.b64decode(post.content)
            sys.stdout.write(f"Decoded video data: {len(video_data)} bytes\n")
            sys.stdout.flush()

            mime_type = 'video/mp4' if post.contentType == 'video/mp4;base64' else 'video/webm'

            response = HttpResponse(video_data, content_type=mime_type)
            return response
        except base64.binascii.Error as e:
            sys.stdout.write(f"Base64 decode error: {str(e)}\n")
            sys.stdout.flush()
            return HttpResponse(f"Base64 decode error: {str(e)}", status=400)
        except Exception as e:
            import traceback
            sys.stdout.write(f"Error processing video: {str(e)}\n")
            sys.stdout.write(traceback.format_exc())
            sys.stdout.flush()
            return HttpResponse(f"Error: {str(e)}", status=500)
    except Post.DoesNotExist:
        sys.stdout.write(f"No post found with internal_id: {post_id}\n")
        sys.stdout.flush()
        return HttpResponse("Post not found", status=404)
    except Exception as e:
        import traceback
        sys.stdout.write(f"Error: {str(e)}\n")
        sys.stdout.write(traceback.format_exc())
        sys.stdout.flush()
        return HttpResponse(f"Error: {str(e)}", status=500)

@api_view(['GET'])
def get_video_with_fqid_fix(request, post_path):
    """Special function to handle URLs that include the /video suffix in the path"""
    if not post_path.endswith('/video'):
        return HttpResponse("Not a video URL", status=400)

    # Remove the /video suffix to get the actual post_fqid
    post_fqid = post_path[:-6]  # Remove '/video'

    # Unquote the post_fqid
    post_fqid = unquote(post_fqid)

    try:
        # Try to find the post
        post = Post.objects.get(id=post_fqid)

        # Make sure it's a video
        if not post.contentType.startswith('video/'):
            return HttpResponse("Not a video post", status=400)

        # Serve the video
        video_data = base64.b64decode(post.content)
        mime_type = 'video/mp4' if post.contentType == 'video/mp4;base64' else 'video/webm'

        return HttpResponse(video_data, content_type=mime_type)
    except Post.DoesNotExist:
        return HttpResponse("Post not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)    