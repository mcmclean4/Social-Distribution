from enum import Enum

from django.db import models

# Create your models here.

# =============================================================================
# Author: Represents a user (local or remote) who can post, follow, etc.
# =============================================================================
class Author(models.Model):
    type = models.CharField(max_length=50)
    # The full API URL for the author. This is unique.
    id = models.URLField(primary_key=True, unique=True)
    host = models.URLField(unique=True)
    # The node that “owns” this author. For remote authors, this points to their home node.
    displayName = models.CharField(max_length=255)
    github = models.URLField(blank=True, null=True)
    profileImage = models.URLField(blank=True, null=True)
    page = models.URLField(blank=True, null=True)  # HTML profile page
    # Flag to indicate if the author is a node administrator.
    isAdmin = models.BooleanField(default=False)

    def __str__(self):
        return self.displayName

class Follow(models.Model):
    type = models.CharField(max_length=50)
    summary = models.CharField()

    follower = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='follower')
    followee = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='followee')

class Comment(models.Model):
    type = models.CharField(max_length=50)

class Comments(models.Model):
    type = models.CharField(max_length=50)

class Like(models.Model):
    type = models.CharField(max_length=50)

class Likes(models.Model):
    type = models.CharField(max_length=50)

class Post(models.Model):
    type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    id = models.URLField(primary_key=True, unique=True)
    page = models.URLField(blank=True, null=True)
    description = models.CharField()
    contentType = models.CharField()
    content = models.CharField()
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    comments = models.ForeignKey(Comments, on_delete=models.CASCADE)
    likes = models.ForeignKey(Likes, on_delete=models.CASCADE)
    published = models.DateTimeField()
    visibility = models.CharField()

class Posts(models.Model):
    type = models.CharField(max_length=50)
    pageNumber = models.IntegerField()
    size = models.IntegerField()
    count = models.IntegerField()
    src = models.ForeignKey(Post, on_delete=models.CASCADE)

