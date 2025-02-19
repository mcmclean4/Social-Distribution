from django.db import models
from django.utils import timezone

# =============================================================================
# Author: Represents a user (local or remote) who can post, follow, etc.
# =============================================================================
class Author(models.Model):
    type = models.CharField(max_length=50)
    # The full API URL for the author. This is unique.
    id = models.URLField(primary_key=True, unique=True, db_index=True)
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


# =============================================================================
# Post: Represents a social media post with likes, comments, etc.
# =============================================================================
class Post(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('text', 'Text'),
        ('markdown', 'Markdown'),
        ('image', 'Image'),
        ('video', 'Video'),
    ]

    CONTENT_VISBILITY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends'),
    ]
    
    type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    id = models.URLField(primary_key=True, unique=True, db_index=True)
    page = models.URLField(blank=True, null=True)
    description = models.CharField(max_length=255)
    contentType = models.CharField(max_length=50, choices=CONTENT_TYPE_CHOICES)
    content = models.CharField(max_length=255)
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    published = models.DateTimeField()
    visibility = models.CharField(max_length=50, choices=CONTENT_VISBILITY_CHOICES)

    # Many-to-many relationship for likes with Author
    likes = models.ManyToManyField(Author, related_name='liked_posts', blank=True, through='PostLike')

    class Meta:
        ordering = ['-published']

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.pk is not None:  # Check if this is an update
            self.edited = timezone.now()
        super().save(*args, **kwargs)


class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)


# =============================================================================
# Comment: Represents a comment on a post.
# =============================================================================
class Comment(models.Model):
    type = models.CharField(max_length=50)
    post = models.ForeignKey(Post, related_name='comments_on_post', on_delete=models.CASCADE)
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

    follower = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='follower')
    followee = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='followee')

    def __str__(self):
        return f"{self.follower.displayName} follows {self.followee.displayName}"
