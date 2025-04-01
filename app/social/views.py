from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView 
from rest_framework.permissions import AllowAny, IsAuthenticated 
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from .serializers import PostSerializer, AuthorSerializer
from .models import Post, Author, Follow, FollowRequest,Inbox, User
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
from django.contrib.admin.sites import site
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection, DatabaseError
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
# Import and call distribute_likes
from .distribution_utils import distribute_likes
# Log the full exception for server-side debugging
import traceback

# Like
from .models import Post, Comment
from .serializers import LikeSerializer
from .models import Like
from .authentication import NodeBasicAuthentication

import requests  # Correct placement of requests import
from django.conf import settings
import json
import os
from rest_framework.pagination import PageNumberPagination
from .utils import *

from .github_activity import fetch_user_activity

def get_base_url(request):
    """Extracts the base URL (protocol + domain) from the request"""
    return f"{request.scheme}://{request.get_host()}"

class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'size'
    max_page_size = 100  # Optional: Prevent very large queries

######################################
#           STREAM/INDEX AREA        
######################################

@login_required
def stream(request):
    friends = get_friends(request.user.author)

    # Check for recent github activity of the current user
    # if request.user.author.github:
    #     if not request.session.get("github_access_token"):
    #         # Redirect the user to the authorization URL
    #         return redirect("social:github_authorize")
        
    #     github_response = fetch_user_activity(request)
    #     if github_response == "invalid_token":
    #         # Token is invalid; redirect the user to reauthorize
    #         return redirect("social:github_authorize")
        

    # Filter posts
    post_list = Post.objects.filtered(
        authors=friends,
        visibilities=['PUBLIC', 'FRIENDS']
    )
        # Add `is_liked` status to each post
    for post in post_list:
        if request.user.is_authenticated:
            try:
                author = request.user.author
                post.is_liked = Like.objects.filter(object=post.id, author=author).exists()
            except:
                post.is_liked = False
        else:
            post.is_liked = False


    # Handle likes for comments
    for post in post_list:
        for comment in post.comments.all():
            if request.user.is_authenticated:
                try:
                    author = request.user.author
                    comment.is_liked = Like.objects.filter(author=author, object=comment.id).exists()
                except:
                    comment.is_liked = False
            else:
                comment.is_liked = False
    # Pagination
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)

    return render(request, 'social/index.html', {'posts': posts})


######################################
#           AUTHOR AREA             
######################################

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.models import User

@csrf_exempt
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

@staff_member_required
def custom_admin_view(request):
    return render(request, 'admin/database.html')

@staff_member_required
def send_command(request):
    data = json.loads(request.body)
    print(data)
    try:
        with connection.cursor() as cursor:
            cursor.execute(data["input_text"])
            result = cursor.fetchall()
            print(str(result))
    except DatabaseError as e:
        result = e
    data = {
        'output': repr(result)
    }
    return JsonResponse(data, status=200)

@staff_member_required
def start_terminal(request):
    
    with connection.cursor() as cursor:
        result = connection.introspection.table_names()
        print(str(result))
    
    data = {
        'output': result
    }
    return JsonResponse(data, status=200)

def register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        displayName = request.POST.get('displayName')
        github = request.POST.get('github')

        # If the GitHub field is empty, set it to None (null)
        if not github.strip():
            github = None

        # Check if the displayName is already taken
        if Author.objects.filter(displayName=displayName).exists():
            messages.error(request, "Display Name already taken. Please choose another.")
            return render(request, 'social/register.html', status=400)

        # Check if the username is already taken
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, 'social/register.html', status=400)

        # Create user but set is_active=False until a superuser approves
        user = User.objects.create_user(username=username, password=password, is_active=False)

        # Get the host from the request
        host_url = request.build_absolute_uri('/').rstrip('/')
        host = f"{host_url}/social/api/"
        
        # Create the Author object with github being None if it was empty
        Author.objects.create(user=user, host=host, displayName=displayName, github=github)

        # Display success message
        messages.success(request, "Your account has been created! A superuser must activate it before you can log in.")
        return redirect('social:login')

    return render(request, 'social/register.html')


@api_view(['GET'])
@authentication_classes([NodeBasicAuthentication])      # for Sid's group
def get_author(request, id):
    """
    Retrieves an author using the correct full ID format.
    """
    base_url = get_base_url(request)  # Get request's base URL dynamically
    full_author_id = f"{base_url}/social/api/authors/{id}"  # Construct the correct ID

    author = get_object_or_404(Author, id=full_author_id)
    serializer = AuthorSerializer(author)
    return Response(serializer.data)

@api_view(['GET'])
@authentication_classes([NodeBasicAuthentication])      # for Sid's group
def get_author_with_fqid(request, author_fqid):
    '''
    Returns an author using the author's fqid
    '''
    author_fqid = unquote(author_fqid)
    author = get_object_or_404(Author, id=author_fqid)
    serializer = AuthorSerializer(author)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([NodeBasicAuthentication])
def get_authors(request):
    """
    Retrieves authors whose `host` starts with the requesting base URL.
    Supports optional pagination with `page` and `size` query parameters.
    If pagination is not requested, returns all authors.
    """
    base_url = get_base_url(request)
    authors = Author.objects.filter(host__startswith=base_url)

    # Get pagination parameters
    page = request.query_params.get('page')
    size = request.query_params.get('size')

    if page and size:  # Apply manual pagination only if both parameters are provided
        try:
            page = int(page)
            size = int(size)
            start = (page - 1) * size
            end = start + size
            authors = authors[start:end]
        except ValueError:
            return Response({"error": "Invalid pagination parameters"}, status=400)
    
    elif page:  # page provided but no size
        try:
            page = int(page)
            size = 1
            start = (page - 1) * size
            end = start + size
            authors = authors[start:end]
        except ValueError:
            return Response({"error": "Invalid pagination parameters"}, status=400)
    
    serializer = AuthorSerializer(authors, many=True)

    return Response({
        "type": "authors",
        "authors": serializer.data
    })

@login_required
def profile_page(request, id):
    """Retrieves the profile page of an author."""
    base_url = get_base_url(request)  # Get the correct host dynamically
    full_author_id = f"{base_url}/social/api/authors/{id}"  # Construct correct ID
    
    # Get the author
    currentAuthor = get_object_or_404(Author, id=full_author_id)
    
    following_number =  len(set(Follow.objects.filter(follower_id=full_author_id).values_list("followee_id", flat=True)))
    follower_number = len(set(Follow.objects.filter(followee_id=full_author_id).values_list("follower_id", flat=True)))
    
    # Get all posts by this author (excluding deleted)
    posts = Post.objects.filter(author=currentAuthor).exclude(visibility="DELETED").values()

    # Format posts for rendering
    postsToRender = []
    for post in posts:
        postDict = {
            "title": post["title"],
            #"image": post["image"],
            "content": post["content"],
            "contentType": post["contentType"],
            "description": post["description"],
            "id": post["internal_id"]
        }
        postsToRender.append(postDict)
        
    return render(request, 'social/profile.html', {"posts": postsToRender, "author": currentAuthor, 'profile_author_id': id, 'followers': follower_number, 'following': following_number})

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .forms import EditProfileForm
from .models import Author

@login_required
def profile_edit(request, id):
    """
    Allows an author to edit their profile.
    """
    base_url = get_base_url(request)  # Get the correct host dynamically
    full_author_id = f"{base_url}/social/api/authors/{id}"  # Construct correct ID

    # Ensure the user is editing their own profile
    currentUser = request.user
    currentAuthor = get_object_or_404(Author, user=currentUser)

    if str(id) != currentAuthor.id.split('/')[-1]:
        return redirect('social:profile_page', id=id)
    
    if request.method == "POST":
        author = get_object_or_404(Author, id=full_author_id)
        form = EditProfileForm(request.POST, instance=author)

        if form.is_valid():
            new_display_name = form.cleaned_data.get('displayName', None)
            if new_display_name and Author.objects.filter(displayName=new_display_name).exclude(id=author.id).exists():
                form.add_error('displayName', 'This display name is already taken. Please choose another.')
                messages.error(request, 'This display name is already taken. Please choose another.')
            else:
                # Save the form data (including profileImage URL)
                form.save()

                # If we reach this point, the form is valid, and the image URL should be saved
                messages.success(request, 'Profile updated successfully!')
                return redirect('social:profile_page', id=id)
        else:
            messages.error(request, 'There was an error updating your profile. Please check the image URL.')

    else:
        form = EditProfileForm(instance=currentAuthor)

    return render(request, 'social/profile_edit.html', {'form': form})



class AuthorPostListAPIView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [AllowAny]  # Allow anyone to list posts

    def get_queryset(self):
        author_id = self.kwargs['author_id']
        return Post.objects.filter(author__id=author_id)
    
class AuthorPostCreateAPIView(generics.CreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]  # Require authentication for creating posts

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
            full_post_id = f"{request.get_host()}/social/posts/{post_id}"
            print(f"Looking for post with ID: {full_post_id}")
            
            post = get_object_or_404(Post, id=full_post_id)
            print(f"Found post: {post.title}")
            
            has_liked = Like.objects.filter(
                object=post.id,
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
        like = Like.objects.filter(
            object=post.id,
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
            # Normalize author_id (remove URL if present)
            if isinstance(author_id, str) and '/authors/' in author_id:
                author_id = author_id.split('/authors/')[-1].split('/')[0]
            
            # Construct the full post URL
            full_post_url = f"{request.get_host()}/social/api/authors/{author_id}/posts/{post_id}"
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
            post_like, created = Like.objects.get_or_create(
                object=post.id,
                author=request_user_author
            )

            if not created:
                # Unlike if already liked
                post_like.delete()
                action = 'unliked'
            else:
                action = 'liked'
                # Send like to the inbox of the post's author
                self.like_to_inbox(post, post_like)
                            # ADDED: Distribute the like to followers if it's a local post
                try:
                    # Check if the post is local
                    current_host = request.get_host()
                    post_author_host = post.author.host.split('//')[1].rstrip('/') if '//' in post.author.host else post.author.host.rstrip('/')
                    
                    is_local_post = not post.author.host or current_host in post_author_host
                    
                    if is_local_post:
                        # Prepare like data for distribution
                        like_data = {
                            "type": "like",
                            "author": {
                                "type": "author",
                                "id": request_user_author.id,
                                "host": request_user_author.host,
                                "displayName": request_user_author.displayName,
                                "page": request_user_author.page,
                                "github": request_user_author.github,
                                "profileImage": request_user_author.profileImage
                            },
                            "published": post_like.published.isoformat(),
                            "id": post_like.id,
                            "object": post.id,
                            "summary": f"{request_user_author.displayName} liked your post"
                        }
                        

                        distribute_likes(post_like, like_data, post.author.id)
                        print(f"[INFO] Distributed like to followers of {post.author.displayName}")
                except Exception as e:
                    import traceback
                    print(f"[ERROR] Error distributing like: {str(e)}")
                    print(traceback.format_exc())
            
            return Response({
                'action': action,
                'like_count': post.likes.count()
            })
        
        except Exception as e:

            traceback.print_exc()
            return Response({
                'error': 'An unexpected error occurred',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    def like_to_inbox(self, post, like):
        '''
        Sends a Like object to the post author's inbox
        '''
        try:
            author_serial = post.author.id.split('/')[-1]
            post_node = Node.objects.get(base_url=post.author.host)
            # Change to use post.author.id instead of author_serial if it turns out inbox should actually use fqid
            inbox_url = f"{post_node.base_url}authors/{author_serial}/inbox"
            print(inbox_url)

            # Create the like object according to the example format
            like_data = {
                "type": "like",
                "author": {
                    "type": "author",
                    "id":like.author.id,
                    "host": like.author.host,
                    "displayName": like.author.displayName,
                    "page": like.author.page,
                    "github": like.author.github,
                    "profileImage": like.author.profileImage
                },
                "published": like.published.isoformat(),
                "id": like.id,
                "object": post.id
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
            print(f"Successfully sent like to {post.author.id}")

        except Node.DoesNotExist:
            print(f"Node does not exist for host: {post.author.host}. May have been removed.")
            pass
        except Exception as e:
            print(f"Failed to send like to {post.author.id}: {str(e)}")
            pass

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
        # Generate Comment URL-based ID
        comment_internal_id = Comment.objects.count() + 1  # Ensure unique ID
        comment_url_id = f"{request_user_author}/{comment_internal_id}"
        print("DEBUG: commentID is", comment_url_id)

        # Create the comment
        comment = Comment.objects.create(
            id=comment_url_id,
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