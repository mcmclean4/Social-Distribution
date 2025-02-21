import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.text import slugify

# =============================================================================
# Author: Represents a user (local or remote) who can post, follow, etc.
# =============================================================================


class Author(models.Model):

    TYPE_CHOICES = [
        ('author', 'author'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    type = models.CharField(
        max_length=50, choices=TYPE_CHOICES, default='author')
    # The full API URL for the author. This is unique.
    id = models.URLField(primary_key=True, unique=True, db_index=True)
    host = models.URLField()
    # The node that “owns” this author. For remote authors, this points to their home node.
    displayName = models.CharField(max_length=255)
    github = models.URLField(blank=True, null=True)
    profileImage = models.URLField(blank=True, null=True)
    page = models.URLField(blank=True, null=True)  # HTML profile page
    # Flag to indicate if the author is a node administrator.
    isAdmin = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self._state.adding:

            last_author = Author.objects.order_by('id').last()
            try:
                largest_current_id = int(last_author.id.split('/')[-1])
            except:
                largest_current_id = 1

            self.id = f"http://localhost:8000/social/api/authors/{largest_current_id+1}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.displayName


# =============================================================================
# Post: Represents a social media post with likes, comments, etc.
# =============================================================================
class Post(models.Model):
    POST_CHOICES = [
        ('post', 'post'),
    ]

    CONTENT_TYPE_CHOICES = [
        ('text/plain', 'Plain Text'),
        ('text/markdown', 'Markdown'),
        ('image/png;base64', 'PNG'),
        ('image/jpeg;base64', 'JPEG'),
    ]

    CONTENT_VISIBILITY_CHOICES = [
        ('PUBLIC', 'Public'),
        ('FRIENDS', 'Friends'),
        ('UNLISTED', 'Unlisted'),
        ('DELETED', 'Deleted'),
    ]

    type = models.CharField(max_length=50, choices=POST_CHOICES, default='post')
    title = models.CharField(max_length=255)
    id = models.URLField(primary_key=True,unique=True, db_index=True)
    page = models.URLField(blank=True, null=True)
    description = models.CharField(max_length=255)
    contentType = models.CharField(max_length=50, choices=CONTENT_TYPE_CHOICES)
    content = models.TextField()
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    author = models.ForeignKey('Author', on_delete=models.CASCADE)
    published = models.DateTimeField()
    visibility = models.CharField(max_length=50, choices=CONTENT_VISIBILITY_CHOICES)
    # is_deleted = models.BooleanField(default=False)

    likes = models.ManyToManyField('Author', related_name='liked_posts', blank=True, through='PostLike')
    comments = models.ManyToManyField('Comment', related_name='post_comments', blank=True)

    class Meta:
        ordering = ['-published']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"http://localhost:8000/posts/{slugify(self.title)}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        if not self.page:
            self.page = f"http://localhost:8000/posts/{slugify(self.title)}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)



class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)


# =============================================================================
# Comment: Represents a comment on a post.
# =============================================================================
class Comment(models.Model):
    type = models.CharField(max_length=50)
    post = models.ForeignKey(
        Post, related_name='comments_on_post', on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    content = models.TextField()
    published = models.DateTimeField()

    class Meta:
        ordering = ['-published']

    def __str__(self):
        return f"Comment by {self.author.displayName} on {self.post.title}"


# =============================================================================
# Follow: Represents a relationship between two authors (follower and followee).
# =============================================================================
class Follow(models.Model):
    type = models.CharField(max_length=50)
    summary = models.CharField(max_length=255)

    follower = models.ForeignKey(
        Author, on_delete=models.CASCADE, related_name='follower')
    followee = models.ForeignKey(
        Author, on_delete=models.CASCADE, related_name='followee')

    def __str__(self):
        return f"{self.follower.displayName} follows {self.followee.displayName}"
