from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import PostSerializer, AuthorSerializer
from .models import Post, Author
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from rest_framework.permissions import IsAuthenticated
from .models import Post, Author
from .forms import PostForm
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required
from .models import Post

class PostListCreateAPIView(generics.ListCreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

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


@login_required
def my_posts(request):
    user = request.user.author

    post_list = Post.objects.filtered(
        filter_type='author',
        authors=[user],
        visibilities=['PUBLIC', 'FRIENDS', 'UNLISTED', 'DELETED']
    )

    # Pagination
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)

    return render(request, 'social/my_posts.html', {'posts': posts})

@login_required
def create_post(request):
    # First check if Author exists for the user
    try:
        author = Author.objects.get(user=request.user)
    except Author.DoesNotExist:
        # Create new Author if doesn't exist
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
                # Get the cleaned data from the form.
                post = form.save(commit=False)
                post.author = author
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
        print(f"Post ID: {internal_id}")
        print(f"Post Author: {post.author.user}")
        print(f"Current User: {request.user}")
        
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

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('social:index')

    else:
        form = PostForm(instance=post)

    return render(request, 'social/update_post.html', {'form': form})


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Post

@login_required
def post_detail(request, internal_id):
    post = get_object_or_404(Post, internal_id=internal_id)
    can_view = False  # Flag to track if the user is allowed to see the post

    # Author can always see their own posts
    if post.author == request.user.author:
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
        author = Author.objects.get(id=f"http://localhost:8000/social/api/authors/{id}")
    except Author.DoesNotExist:
        return Response({'error': 'Author not found'}, status=status.HTTP_404_NOT_FOUND)
    
    posts = Post.objects.filter(author=author)
    post_serializer = PostSerializer(posts, many=True)

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
            author = Author.objects.get(id=f"http://localhost:8000/social/api/authors/{author_id}")
            
            # Get the post by internal_id and make sure it's linked to the correct author
            post = Post.objects.get(internal_id=internal_id, author=author)
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
        post_url = f"http://localhost:8000/social/api/authors/2/posts/{id}"
        
        print(f"Attempting to fetch post with URL: {post_url}")
        
        post = Post.objects.get(id=post_url)
        print(f"Post found: {post}")
    except Post.DoesNotExist:
        print(f"Post with ID {id} not found.")
        return Response({'error': 'Post not found'}, status=404)

    post_serializer = PostSerializer(post)

    print(f"Serialized Post Data: {post_serializer.data}")

    return Response(post_serializer.data)