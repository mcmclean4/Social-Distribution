from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from rest_framework import generics
from .models import Post
from .serializers import PostSerializer
from django.shortcuts import render, redirect, get_object_or_404
from .forms import PostForm
from django.contrib.auth.models import User
from .models import Author
from django.core.paginator import Paginator
from django.views import View

def stream(request):
    post_list = Post.objects.filter(is_deleted=False).order_by('-published')
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    return render(request, 'social/index.html', {'posts': posts})

class PostListCreateAPIView(generics.ListCreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user.author) 

def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            if request.user.is_authenticated and hasattr(request.user, 'author'):
                post.author = request.user.author
            else:
                default_user, created = User.objects.get_or_create(username='anonymous_user', defaults={'password': 'password'})
                post.author, created = Author.objects.get_or_create(
                    user=default_user,
                    defaults={
                        'id': f'http://localhost:8000/authors/{default_user.username}',
                        'displayName': 'Anonymous Author',
                        'host': 'http://localhost:8000',
                        'type': 'Author'
                    }
                )
            post.published = timezone.now()
            post.save()
            return redirect('social:index')
    else:
        form = PostForm()
    return render(request, 'social/create_post.html', {'form': form})

def update_post(request, auto_id):
    post = get_object_or_404(Post, auto_id=auto_id)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('social:index')
    else:
        form = PostForm(instance=post)
    return render(request, 'social/update_post.html', {'form': form, 'post': post})

def delete_post(request, auto_id):
    post = get_object_or_404(Post, auto_id=auto_id)
    if request.method == 'POST':
        post.is_deleted = True
        post.save()
        return redirect('social:index')
    return render(request, 'social/delete_post.html', {'post': post})


def post_detail(request, auto_id):
    post = get_object_or_404(Post, auto_id=auto_id)
    return render(request, 'social/post_detail.html', {'post': post})