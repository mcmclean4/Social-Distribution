from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import PostSerializer, AuthorSerializer
from .models import Post, Author
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Post, Author
from .forms import PostForm
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required
from urllib.parse import unquote
from .models import Post
import sys
import uuid
import base64
from io import BytesIO
from PIL import Image

class PostListCreateAPIView(generics.ListCreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        # Ensure the author is created or retrieved for the current user
        author, created = Author.objects.get_or_create(
            user=self.request.user,
            defaults={"type": "author", "displayName": self.request.user.username}
        )
        serializer.save(author=author)

    def perform_destroy(self, instance):
        # Instead of deleting, mark the post as deleted
        instance.visibility = 'DELETED'
        instance.save()

class PostDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    lookup_field = 'internal_id'  # Using `internal_id` as the lookup field

    def get_object(self):
        # Fetch the post using its `internal_id`
        return Post.objects.get(internal_id=self.kwargs['internal_id'])

    def perform_update(self, serializer):
        # You can add additional logic here if needed for updates
        serializer.save()

    def perform_destroy(self, instance):
        # Instead of deleting, mark the post as deleted
        instance.visibility = 'DELETED'
        instance.save()

@api_view(['GET'])
@login_required
def get_post_with_fqid(request, post_fqid):
    '''
    Returns a post using the post's fqid
    '''
    post_fqid = unquote(post_fqid)
    post = get_object_or_404(Post, id=post_fqid)

    can_view = False  # Flag to track if the user is allowed to see the post

    # Author can always see their own posts
    if post.author == request.user.author and post.visibility != 'DELETED':
        can_view = True

    elif post.visibility == 'PUBLIC':
        can_view = True

    elif post.visibility == 'FRIENDS':
        if request.user.is_authenticated and request.user.author in post.author.friends:
            can_view = True

    elif post.visibility == 'UNLISTED':
        can_view = True  # Anyone with the link can view

    if not can_view or post.visibility == 'DELETED':
        # Return 403 forbidden code
        return Response({"detail": "You do not have permission to view this post."}, status=status.HTTP_403_FORBIDDEN)
        
    serializer = PostSerializer(post)
    return Response(serializer.data)



@login_required
def my_posts(request):
    user = request.user.author

    # Fetch posts
    post_list = Post.objects.filtered(
        filter_type='author',
        authors=[user],
        visibilities=['PUBLIC', 'FRIENDS', 'UNLISTED']
    )

    # Debugging: Print all fetched posts (force flush)
    print("Retrieved Posts:", post_list.values_list("title", "visibility"), flush=True)
    sys.stdout.flush()  # Force immediate output

    # Pagination
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)

    return render(request, 'social/my_posts.html', {'posts': posts})

@login_required
def create_post(request):
    print("\n========= CREATE POST DEBUG =========")
    print(f"Request method: {request.method}")

    if request.method == "POST":
        print(f"POST data keys: {list(request.POST.keys())}")
        print(f"FILES data keys: {list(request.FILES.keys())}")

        # Log content type specifically
        if 'contentType' in request.POST:
            print(f"Selected content type: {request.POST['contentType']}")
        else:
            print("WARNING: No contentType in POST data")    
    try:
        author = Author.objects.get(user=request.user)
    except Author.DoesNotExist:
        author = Author.objects.create(
            user=request.user,
            type='author',
            displayName=request.user.username,
        )
        author.save()
    
    try:
        if request.method == "POST":
            form = PostForm(request.POST, request.FILES)
            if form.is_valid():
                post = form.save(commit=False)
                post.author = author
                
                content_type = form.cleaned_data['contentType']

                video_file = request.FILES.get('video')
                image_file = request.FILES.get('image')
                print(f"Image file present: {image_file is not None}")
                print(f"Video file present: {video_file is not None}")

                # Handle image upload if present
                if image_file and ('image/' in content_type or content_type == 'application/base64'):
                    image = request.FILES['image']
                    
                    # Determine content type based on image format
                    img_format = image.name.split('.')[-1].lower()
                    if img_format == 'png':
                        post.contentType = 'image/png;base64'
                    elif img_format in ['jpg', 'jpeg']:
                        post.contentType = 'image/jpeg;base64'
                    else:
                        post.contentType = 'application/base64'
                    
                    # Convert image to base64
                    image_data = base64.b64encode(image.read()).decode('utf-8')
                    post.content = image_data
                # Handle video upload
                elif video_file and 'video/' in content_type:
                    print("Processing video upload")
                    print(f"Video details: name={video_file.name}, size={video_file.size}")

                    # Determine content type based on video format
                    video_format = video_file.name.split('.')[-1].lower()
                    print(f"Detected video format: {video_format}")

                    if video_format == 'mp4':
                        post.contentType = 'video/mp4;base64'
                    elif video_format == 'webm':
                        post.contentType = 'video/webm;base64'
                    else:
                        # Default to mp4 if format not recognized
                        post.contentType = 'video/mp4;base64'

                    print(f"Set post content type to: {post.contentType}")

                    # Check file size (50MB limit)
                    max_size = 50 * 1024 * 1024  # 50MB
                    if video_file.size > max_size:
                        print(f"Video too large: {video_file.size} > {max_size}")
                        messages.error(request, "Video file is too large. Maximum size is 50MB.")
                        return render(request, 'social/create_post.html', {'form': form})

                    try:
                        # Convert video to base64
                        print("Starting video conversion to base64...")
                        video_data = base64.b64encode(video_file.read()).decode('utf-8')
                        post.content = video_data
                        print(f"Video encoded to base64, length: {len(video_data)}")
                    except Exception as e:
                        print(f"Error encoding video: {str(e)}")
                        import traceback
                        print(traceback.format_exc())
                        messages.error(request, f"Error processing video: {str(e)}")
                        return render(request, 'social/create_post.html', {'form': form})
                else:
                    # Normal text content
                    print(f"Using text content for content type {content_type}")
                    post.content = form.cleaned_data.get('content', '')                
                post.save()
                return redirect('social:index')
        else:
            form = PostForm()
        
        return render(request, 'social/create_post.html', {'form': form})
    
    except Exception as e:
        print(f"Error creating post: {str(e)}")
        messages.error(request, "Error creating post. Please try again.")
    
    form = PostForm()
    return render(request, 'social/create_post.html', {'form': form})

@login_required
def delete_post(request, internal_id):
    try:
        # First try to get the post without author check
        post = Post.objects.get(internal_id=internal_id)
        
        # Print debug information
        # print(f"Post ID: {internal_id}")
        # print(f"Post Author: {post.author.user}")
        # print(f"Current User: {request.user}")
        
        # Then check if user is author
        if post.author.user != request.user:
            print("User is not the author")
            return redirect('social:index')
            
        if request.method == "POST":
            post.visibility = 'DELETED'
            post.save()
            # print(f"Post {internal_id} marked as deleted") 
            return redirect('social:index')
            
    except Post.DoesNotExist:
        print(f"No post found with ID: {internal_id}")
        
    return redirect('social:index')

@login_required
def update_post(request, internal_id):
    post = get_object_or_404(Post, internal_id=internal_id, author__user=request.user)
    
    try:
        if request.method == "POST":
            form = PostForm(request.POST, request.FILES, instance=post)
            if form.is_valid():
                updated_post = form.save(commit=False)
                
                # Handle image upload if present
                if 'image' in request.FILES:
                    image = request.FILES['image']
                    # Convert image to base64
                    image_data = base64.b64encode(image.read()).decode('utf-8')
                    updated_post.content = image_data
                
                updated_post.save()
                return redirect('social:index')
        else:
            form = PostForm(instance=post)
        
        return render(request, 'social/update_post.html', {'form': form, 'post': post})
    
    except Exception as e:
        print(f"Error updating post: {str(e)}")
        messages.error(request, "Error updating post. Please try again.")
        
        form = PostForm(instance=post)
    return render(request, 'social/update_post.html', {'form': form, 'post': post})

@login_required
def post_detail(request, internal_id):
    post = get_object_or_404(Post, internal_id=internal_id)
    can_view = False  # Flag to track if the user is allowed to see the post

    # Author can always see their own posts
    if post.author == request.user.author and post.visibility != 'DELETED':
        can_view = True

    elif post.visibility == 'PUBLIC':
        can_view = True

    elif post.visibility == 'FRIENDS':
        if request.user.is_authenticated and request.user.author in post.author.friends:
            can_view = True

    elif post.visibility == 'UNLISTED':
        can_view = True  # Anyone with the link can view

    elif post.visibility == 'DELETED':
        message = "This post has been deleted."
        return render(request, 'social/restricted_post.html', {'message': message})

    if not can_view:
        message = "You do not have permission to view this post."
        return render(request, 'social/restricted_post.html', {'message': message})

    # Add like count for comments
    for comment in post.comments.all():
        comment.like_count = comment.get_likes_count()

    return render(request, 'social/post_detail.html', {'post': post})


@api_view(['PUT'])
def api_update_post(request, internal_id):
    try:
        post = Post.objects.get(internal_id=internal_id)
    except Post.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = PostSerializer(post, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def api_delete_post(request, internal_id):
    try:
        post = Post.objects.get(internal_id=internal_id)
    except Post.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    
    post.delete()
    return Response({"detail": "Post deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
def api_get_author_and_all_post(request, id):
    try:
        author = Author.objects.get(id=f"http://{request.get_host()}/social/api/authors/{id}")
    except Author.DoesNotExist:
        return Response({'error': 'Author not found'}, status=status.HTTP_404_NOT_FOUND)
    
    posts = Post.objects.filter(author=author)

  
    post_serializer = PostSerializer(posts, many=True, context={'request': request})

    author_serializer = AuthorSerializer(author)

    return Response({
        'author': author_serializer.data,
        'posts': post_serializer.data
    })


@api_view(['GET', 'PUT', 'DELETE'])
def get_author_and_post(request, author_id, internal_id):
    if (request.method == "GET"):
        try:
            # Get the author by id
            author = get_object_or_404(Author, id__endswith=f"/social/api/authors/{author_id}")
            # Retrieve the post
            post = get_object_or_404(Post, internal_id=internal_id, author=author)

        except Author.DoesNotExist:
            return Response({'error': 'Author not found'}, status=status.HTTP_404_NOT_FOUND)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

        post_serializer = PostSerializer(post)

        response_data = {
            'post': post_serializer.data
        }

        return Response(response_data)
    elif (request.method == "PUT"):
        # request.method == "PUT", call update function
        # return api_update_post(request, internal_id)
        # ** Temporarily copied the content of api_update_post to avoid issue where request's type changed
        try:
            post = Post.objects.get(internal_id=internal_id)
        except Post.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = PostSerializer(post, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        # request is DELETE, copying from api_p
        try:
            post = Post.objects.get(internal_id=internal_id)
        except Post.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        
        post.visibility = "DELETED"
        post.save()
        return Response({"detail": "Post deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def api_get_post_by_id(request, id):
    try:
        # Construct the full URL for the post
        post_url = f"http://{request.get_host()}/social/api/authors/2/posts/{id}"
        
        print(f"Attempting to fetch post with URL: {post_url}")
        
        post = Post.objects.get(id=post_url)
        print(f"Post found: {post}")
    except Post.DoesNotExist:
        print(f"Post with ID {id} not found.")
        return Response({'error': 'Post not found'}, status=404)

    post_serializer = PostSerializer(post)

    print(f"Serialized Post Data: {post_serializer.data}")

    return Response(post_serializer.data)

@login_required
def create_video_post(request):
    try:
        author = Author.objects.get(user=request.user)
    except Author.DoesNotExist:
        author = Author.objects.create(
            user=request.user,
            type='author',
            displayName=request.user.username,
        )
        author.save()

    try:
        if request.method == "POST":
            form = PostForm(request.POST, request.FILES)
            if form.is_valid():
                post = form.save(commit=False)
                post.author = author

                # Handle video upload if present
                if 'video' in request.FILES:
                    video = request.FILES['video']

                    # Determine content type based on video format
                    video_format = video.name.split('.')[-1].lower()
                    if video_format == 'mp4':
                        post.contentType = 'video/mp4;base64'
                    elif video_format == 'webm':
                        post.contentType = 'video/webm;base64'
                    else:
                        # Default to mp4 if format not recognized
                        post.contentType = 'video/mp4;base64'

                    # Limit video size (optional, adjust max_size as needed)
                    max_size = 50 * 1024 * 1024  # 50MB max size
                    if video.size > max_size:
                        messages.error(request, "Video file is too large. Maximum size is 50MB.")
                        return render(request, 'social/create_video_post.html', {'form': form})

                    # Convert video to base64
                    video_data = base64.b64encode(video.read()).decode('utf-8')
                    post.content = video_data
                else:
                    messages.error(request, "Please upload a video file.")
                    return render(request, 'social/create_video_post.html', {'form': form})

                post.save()
                return redirect('social:index')
        else:
            form = PostForm()

        return render(request, 'social/create_video_post.html', {'form': form})

    except Exception as e:
        print(f"Error creating video post: {str(e)}")
        messages.error(request, "Error creating video post. Please try again.")

    form = PostForm()
    return render(request, 'social/create_video_post.html', {'form': form})
