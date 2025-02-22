from django.db import models
from django.contrib.auth.models import User

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
    id = models.URLField(primary_key=True, unique=True)

    #host is not unique
    #host = models.URLField(unique=True)
    host = models.URLField(null=True, blank=True)  # ✅ Allow duplicate hosts

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
    id = models.URLField(primary_key=True, unique=True)  # This will be the custom URL for the post
    page = models.URLField(blank=True, null=True)  # Optionally, the page URL for the post
    description = models.CharField(max_length=255)
    contentType = models.CharField(max_length=50, choices=CONTENT_TYPE_CHOICES)
    content = models.TextField()
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)  # Linking the post to the author (User model)
    published = models.DateTimeField(auto_now_add=True)  # Automatically set the published time when creating the post
    visibility = models.CharField(max_length=50, choices=CONTENT_VISIBILITY_CHOICES)

    likes = models.ManyToManyField('Author', related_name='liked_posts', blank=True, through='PostLike')
    comments = models.ManyToManyField('Comment', related_name='post_comments', blank=True)

    class Meta:
        ordering = ['-published']  # Sorting posts by latest published date

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self._state.adding:
            largest_current_id = Post.objects.order_by('id').last()
            try:
                largest_current_id = int(largest_current_id.id.split('/')[-1])
            except:
                largest_current_id = 1
            # Extract the author ID from the author URL
            author_id = self.author.id.split('/')[-1]
            self.id = f"http://localhost:8000/social/api/authors/{author_id}/posts/{largest_current_id+1}"
        super().save(*args, **kwargs)  # Call the real save() method


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

class FollowRequest(models.Model):
    """
    Represents a follow request stored in the inbox of the followee.
    """
    summary = models.CharField(max_length=255, blank=True)
    follower_id = models.CharField(max_length=255)  # Store remote/local follower as FQID       #Follower does not have to be author in our node
    followee = models.ForeignKey('Author', on_delete=models.CASCADE, related_name='follow_requests')

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower_id", "followee")  # Prevent duplicate follow requests

    def __str__(self):
        return f"{self.follower_id} -> {self.followee.display_name} ({self.status})"



class Follow(models.Model):
    """
    Represents an actual follow relationship after approval.
    """
    follower_id = models.CharField(max_length=255)  # Store remote/local follower as FQID
    followee = models.ForeignKey('Author', on_delete=models.CASCADE, related_name='followers')

    class Meta:
        unique_together = ("follower_id", "followee")  # Prevent duplicate follow entries

    def __str__(self):
        return f"{self.follower_id} follows {self.followee.display_name}"

class Comments(models.Model):
    type = models.CharField(max_length=50)

class Like(models.Model):
    type = models.CharField(max_length=50)

class Likes(models.Model):
    type = models.CharField(max_length=50)


class Posts(models.Model):
    type = models.CharField(max_length=50)
    pageNumber = models.IntegerField()
    size = models.IntegerField()
    count = models.IntegerField()
    src = models.ForeignKey(Post, on_delete=models.CASCADE)

class Inbox(models.Model):
    author = models.ForeignKey('Author', on_delete=models.CASCADE)
    type = models.CharField(max_length=30, default='inbox')
    inbox_posts = models.ManyToManyField(Posts,blank = True)
    inbox_likes = models.ManyToManyField(Like, blank=True)
    inbox_follows = models.ManyToManyField(FollowRequest, blank=True)
    inbox_comments = models.ManyToManyField(Comments,  blank=True)