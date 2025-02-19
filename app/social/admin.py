from django.contrib import admin
from django.contrib.auth.models import User
from .models import Author, Post, Comment, Follow
# Register your models here.

admin.site.register(Author)
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Follow)