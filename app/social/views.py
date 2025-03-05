from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView 
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from .serializers import PostSerializer, AuthorSerializer
from .models import Post, Author, Follow, FollowRequest,Inbox
import requests
from django.shortcuts import render, redirect, get_object_or_404
from .forms import PostForm, EditProfileForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.views import View
from django.views.generic import ListView
from django.contrib import messages
from urllib.parse import unquote
from django.db import transaction  # Correct placement of transaction import
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from .models import Post, Author

# Like
from .models import Post, PostLike, Comment
from .serializers import PostLikeSerializer

import requests  # Correct placement of requests import
from django.conf import settings
import json
import os
from rest_framework.pagination import PageNumberPagination
from .utils import *


######################################
#           STREAM/INDEX AREA        
######################################

@login_required
def stream(request):
    friends = get_friends(request.user.author)

    # Filter posts
    post_list = Post.objects.filtered(
        authors=friends,
        visibilities=['PUBLIC', 'FRIENDS']
    )

    # Handle likes for comments
    for post in post_list:
        post.is_liked = PostLike.objects.filter(post=post, author=request.user.author).exists()
        for comment in post.comments.all():
            comment.is_liked = request.user.author in comment.likes.all() if request.user.is_authenticated else False

    # Pagination
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)

    return render(request, 'social/index.html', {'posts': posts})


######################################
#           AUTHOR AREA             
######################################


# def login_page(request):
#     if request.method == "POST":
#         username = request.POST.get('username')
#         password = request.POST.get('password')

#         if not User.objects.filter(username=username).exists():
#             messages.error(request, 'Username does not exist')
#             return redirect('social:login')

#         user = authenticate(username=username, password=password)

#         if user is None:
#             messages.error(request, 'Password does not match username')
#             return redirect('social:login')

#         else:
#             login(request, user)
#             return redirect('social:index')

#     return render(request, 'social/login.html')

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.models import User

def login_page(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Check if the user exists
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, 'Username does not exist. Please register.')
            return redirect('social:login')

        # Authenticate the user
        user = authenticate(username=username, password=password)

        if user is None:
            messages.error(request, 'Password does not match username.')
            return redirect('social:login')

        # Check if the account is active
        if not user.is_active:
            messages.error(request, 'Your account is not active. Please wait for admin approval.')
            return redirect('social:login')

        # Log the user in
        login(request, user)
        return redirect('social:index')

    return render(request, 'social/login.html')


def logout_page(request):
    logout(request)
    return redirect('social:login')


# def register(request):
#     if request.method == "POST":
#         print(request.POST)
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         displayName = request.POST.get('displayName')

#         if User.objects.filter(username=username).exists():
#             messages.error(request, "Username already taken.")
#             # return 400 since new user is not created
#             return render(request, 'social/register.html', status=400)

#         user = User.objects.create_user(username=username, password=password)

#         host = "http://localhost:8000/social/api/"

#         author = Author.objects.create(
#             user=user, host=host, displayName=displayName)

#         author.save()

#         user = authenticate(request, username=username, password=password)
#         if user is not None:
#             login(request, user)
#             return redirect('social:index')

#         # create_author()

#     return render(request, 'social/register.html')

def register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        displayName = request.POST.get('displayName')
        github = request.POST.get('github')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, 'social/register.html', status=400)

        # Create user but set is_active=False until a superuser approves
        user = User.objects.create_user(username=username, password=password, is_active=False)

        host = "http://localhost:8000/social/api/"
        Author.objects.create(user=user, host=host, displayName=displayName, github=github)

        messages.success(request, "Your account has been created! A superuser must activate it before you can log in.")
        return redirect('social:login')

    return render(request, 'social/register.html')

@api_view(['GET'])
def get_author(request, id):
    author = get_object_or_404(Author, id=f"http://localhost:8000/social/api/authors/{id}")
    serializer = AuthorSerializer(author)
    return Response(serializer.data)

@api_view(['GET'])
def get_authors(request):
    authors = Author.objects.all()
    serializer = AuthorSerializer(authors, many=True)
    return Response(serializer.data)

@login_required
def profile_page(request, id):
    #Get the author
    currentAuthor = Author.objects.filter(id=f"http://localhost:8000/social/api/authors/{id}").get()
    
    #Get all the posts
    posts = Post.objects.filter(author=currentAuthor).values()
    
    #We need type
    postsToRender = []
    for post in posts:
        print(post["id"])
        postDict = {
            "title": post["title"],
            "image": post["image"],
            "content": post["content"],
            "contentType": post["contentType"],
            "description": post["description"],
            "id": post["internal_id"]
        }
        postsToRender.append(postDict)
        
    return render(request, 'social/profile.html', {"posts": postsToRender, "author":currentAuthor, 'profile_author_id':id})

@login_required
def profile_edit(request, id):
    if request.POST:
        author = Author.objects.filter(id = f"http://localhost:8000/social/api/authors/{id}").get()
        form = EditProfileForm(request.POST, request.FILES, instance=author)
        print("VALID")
        if form.is_valid():
            
            form.save()
            return redirect('social:profile_page', id=id)
    currentUser = request.user
    currentAuthor = Author.objects.filter(user=currentUser).get()
    form = EditProfileForm(request.POST, request.FILES, instance=currentAuthor)
    if str(id) != currentAuthor.id.split('/')[-1]:
        return redirect('social:profile_page', id=id)
    else:
        print("correct")
    return render(request, 'social/profile_edit.html', {'form': form})


class AuthorPostListAPIView(generics.ListAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        author_id = self.kwargs['author_id']
        return Post.objects.filter(author__id=author_id)
    
class AuthorPostCreateAPIView(generics.CreateAPIView):
    serializer_class = PostSerializer

    def perform_create(self, serializer):
        author = Author.objects.get(id=self.kwargs['author_id'])
        serializer.save(author=author)


######################################
#           POST/INBOX AREA              
######################################

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

######################################
#           FOLLOW/FOLLOWEE AREA      
######################################


class PostLikeView(APIView):
    def get(self, request, author_id, post_id):
        """Check if the current user has liked the post"""
        try:
            # Construct the full post ID
            full_post_id = f"http://localhost:8000/posts/{post_id}"
            print(f"Looking for post with ID: {full_post_id}")
            
            post = get_object_or_404(Post, id=full_post_id)
            print(f"Found post: {post.title}")
            
            has_liked = PostLike.objects.filter(
                post=post,
                author=request.user.author
            ).exists()
            
            return Response({"has_liked": has_liked})
            
        except Post.DoesNotExist:
            return Response(
                {"error": f"Post not found with ID: {full_post_id}"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    def delete(self, request, author_id, post_id):
        """Remove a like from the post"""
        post = get_object_or_404(Post, id=f"http://localhost:8000/posts/{post_id}")
        like = PostLike.objects.filter(
            post=post,
            author=request.user.author
        )
        
        if like.exists():
            like.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        return Response(
            {"message": "Like not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    def post(self, request, author_id, post_id):
        try:
            # Debug prints
            # print("\n--- Post Like Debugging ---")
            # print(f"Request User: {request.user.username}")
            # print(f"Raw Author ID: {author_id}")
            # print(f"Raw Post ID: {post_id}")
            
            # Normalize author_id (remove URL if present)
            if isinstance(author_id, str) and '/authors/' in author_id:
                author_id = author_id.split('/authors/')[-1].split('/')[0]
            
            # Construct the full post URL
            full_post_url = f"http://localhost:8000/social/api/authors/{author_id}/posts/{post_id}"
            print(f"Constructed Post URL: {full_post_url}")
            
            # Find the post
            try:
                # Try to find the post by its full URL ID first
                post = Post.objects.get(id=full_post_url)
            except Post.DoesNotExist:
                # Fallback to finding by internal_id
                try:
                    post = Post.objects.get(internal_id=post_id)
                except Post.DoesNotExist:
                    # Log all existing posts for debugging
                    all_posts = Post.objects.all()
                    print("All Posts in Database:")
                    for p in all_posts:
                        print(f"Full ID: {p.id}")
                        print(f"Internal ID: {p.internal_id}")
                        print(f"Author ID: {p.author.id}")
                        print(f"Title: {p.title}")
                        print("---")
                    
                    return Response({
                        'error': 'Post not found', 
                        'details': {
                            'full_url': full_post_url,
                            'author_id': author_id,
                            'post_id': post_id
                        }
                    }, status=status.HTTP_404_NOT_FOUND)
            
            # Get or create the author profile for the current user
            try:
                request_user_author = request.user.author
            except Author.DoesNotExist:
                request_user_author = Author.objects.create(
                    user=request.user,
                    type='author',
                    displayName=request.user.username,
                )
            
            # Check if like already exists
            post_like, created = PostLike.objects.get_or_create(
                post=post,
                author=request_user_author
            )
            
            if not created:
                # Unlike if already liked
                post_like.delete()
                action = 'unliked'
            else:
                action = 'liked'
            
            return Response({
                'action': action,
                'like_count': post.likes.count()
            })
        
        except Exception as e:
            # Log the full exception for server-side debugging
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'An unexpected error occurred',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# comments
@api_view(['POST'])
def add_comment(request, author_id, post_id):
    try:
        # Debug prints
        print("\n--- Add Comment Debugging ---")
        print(f"Request User: {request.user.username}")
        print(f"Raw Author ID: {author_id}")
        print(f"Raw Post ID: {post_id}")
        
        # Normalize author_id (remove URL if present)
        if isinstance(author_id, str) and '/authors/' in author_id:
            author_id = author_id.split('/authors/')[-1].split('/')[0]
        
        # Construct the full post URL
        full_post_url = f"http://localhost:8000/social/api/authors/{author_id}/posts/{post_id}"
        
        # Parse comment content
        content = request.data.get('content', '').strip()
        
        # Validate comment content
        if not content:
            return Response({
                'error': 'Comment content cannot be empty'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find the post
        try:
            # Try to find the post by its full URL ID first
            post = Post.objects.get(id=full_post_url)
        except Post.DoesNotExist:
            # Fallback to finding by internal_id
            try:
                post = Post.objects.get(internal_id=post_id)
            except Post.DoesNotExist:
                return Response({
                    'error': 'Post not found', 
                    'details': {
                        'full_url': full_post_url,
                        'author_id': author_id,
                        'post_id': post_id
                    }
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Get or create the author profile for the current user
        try:
            request_user_author = request.user.author
        except Author.DoesNotExist:
            request_user_author = Author.objects.create(
                user=request.user,
                type='author',
                displayName=request.user.username,
            )
        
        # Create the comment
        comment = Comment.objects.create(
            type='comment',
            post=post,
            author=request_user_author,
            content=content,
            published=timezone.now()
        )
        
        # Add comment to post
        post.comments.add(comment)
        
        # Prepare response data
        return Response({
            'id': comment.id,
            'content': comment.content,
            'published': comment.published.isoformat(),
            'author': {
                'id': comment.author.id,
                'displayName': comment.author.displayName
            },
            'post': {
                'id': post.id,
                'internal_id': post.internal_id
            }
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        # Log the full exception for server-side debugging
        import traceback
        traceback.print_exc()
        return Response({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CommentLikeView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request, author_id, post_id, comment_id):
        try:
            # Debug prints
            print("\n--- Comment Like Debugging ---")
            print(f"Request User: {request.user.username}")
            print(f"Raw Author ID: {author_id}")
            print(f"Raw Post ID: {post_id}")
            print(f"Raw Comment ID: {comment_id}")
            
            # Normalize author_id (remove URL if present)
            if isinstance(author_id, str) and '/authors/' in author_id:
                author_id = author_id.split('/authors/')[-1].split('/')[0]
            
            # Construct the full post URL
            full_post_url = f"http://localhost:8000/social/api/authors/{author_id}/posts/{post_id}"
            
            # Find the post
            try:
                # Try to find the post by its full URL ID first
                post = Post.objects.get(id=full_post_url)
            except Post.DoesNotExist:
                # Fallback to finding by internal_id
                try:
                    post = Post.objects.get(internal_id=post_id)
                except Post.DoesNotExist:
                    return Response({
                        'error': 'Post not found', 
                        'details': {
                            'full_url': full_post_url,
                            'author_id': author_id,
                            'post_id': post_id
                        }
                    }, status=status.HTTP_404_NOT_FOUND)
            
            # Find the comment
            try:
                comment = Comment.objects.get(id=comment_id)
            except Comment.DoesNotExist:
                return Response({
                    'error': 'Comment not found', 
                    'details': {
                        'comment_id': comment_id
                    }
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get or create the author profile for the current user
            try:
                request_user_author = request.user.author
            except Author.DoesNotExist:
                request_user_author = Author.objects.create(
                    user=request.user,
                    type='author',
                    displayName=request.user.username,
                )
            
            # Check if like already exists
            like_exists = comment.likes.filter(id=request_user_author.id).exists()
            
            if like_exists:
                # Unlike
                comment.likes.remove(request_user_author)
                action = 'unliked'
            else:
                # Like
                comment.likes.add(request_user_author)
                action = 'liked'
            
            return Response({
                'action': action,
                'like_count': comment.likes.count()
            })
        
        except Exception as e:
            # Log the full exception for server-side debugging
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'An unexpected error occurred',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)