import json
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from social.models import Author, Post, Comment, Like
from django.conf import settings

class CommentsLikesAPITests(TestCase):
    def setUp(self):
        settings.HOST = "http://localhost:8000/social/"
        
        # Create test users
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")

        # Create test authors
        self.author1 = Author.objects.create(user=self.user1, displayName="Lara Croft", host=settings.HOST)
        self.author2 = Author.objects.create(user=self.user2, displayName="Greg Johnson", host=settings.HOST)

        # Extract author ID
        author_id = self.author1.id.split('/')[-1]

        self.post = Post.objects.create(
            author=self.author1,
            title="Test Post",
            content="This is a test post."
        )
        
        # Refresh to get the posttid
        self.post.refresh_from_db()
        self.post_id = self.post.id  # Store the actual ID assigned

        # Initialize API client
        self.client = APIClient()
        self.client.force_login(self.user2)


    
    def test_add_comment(self):
        """Test adding a comment to a post
        api: POST: api/authors/author_id/posts/post_serial/comments/
        """

        # Extract author ID to match post format
        author_id = self.author1.id.split('/')[-1]
        post_id = self.post_id  # Use actual post ID

        # Construct API URL
        post_serial = post_id.split('/')[-1]  # Extracts just the number
        url = reverse("social:post_comments", kwargs={"author_id": author_id, "post_serial": post_serial})

        data = {
            "type": "comment",
            "comment": "This is a new test comment.",
            "contentType": "text/plain",
            "author": {
                "id": self.author2.id,
                "displayName": self.author2.displayName
            },
            "post": post_id  # Ensure the correct post ID is used
        }

        response = self.client.post(url, data, format="json")

        # Debugging output

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["comment"], "This is a new test comment.")

        # Verify the comment is in the database
        self.assertEqual(Comment.objects.filter(post=post_id).count(), 1)

    def test_get_post_comments(self):
        """Test retrieving comments for a post through API"""

        # Ensure the test uses the correct post ID
        author_id = self.author1.id.split('/')[-1]
        post_id = self.post_id  # Use actual post ID
        post_serial = post_id.split('/')[-1]  # Extract the last part of the ID

        # Create comments in the test database
        Comment.objects.create(
            author=self.author2,
            comment="First test comment.",
            post=post_id
        )

        Comment.objects.create(
            author=self.author1,
            comment="Second test comment.",
            post=post_id
        )

        # Construct API URL
        url = reverse("social:post_comments", kwargs={"author_id": author_id, "post_serial": post_serial})

        # Send GET request to retrieve comments
        response = self.client.get(url)

        # Ensure request was successful
        self.assertEqual(response.status_code, 200)

        # Ensure correct response type
        self.assertEqual(response.data["type"], "comments")

        # Ensure the correct number of comments is returned
        self.assertEqual(len(response.data["comments"]), 2)

        # Ensure the latest comment matches the expected one
        self.assertEqual(response.data["comments"][0]["comment"], "Second test comment.")  # Latest comment
        self.assertEqual(response.data["comments"][-1]["comment"], "First test comment.")  # Oldest comment


    def test_like_comment(self):
        """Test liking and unliking a comment"""

        # Ensure correct IDs are used
        author_id = self.author1.id.split('/')[-1]
        post_id = self.post_id  
        post_serial = post_id.split('/')[-1]  # Extracts just the number

        # Create a comment in the test database
        self.comment = Comment.objects.create(
            author=self.author2,
            comment="A comment to like.",
            post=post_id
        )
        comment_fqid = self.comment.id.split("/")[-1]  # Extract the comment identifier

        # Construct API URL for liking a comment
        url = reverse("social:like_comment", kwargs={
            "author_id": author_id,
            "post_id": post_serial,
            "comment_fqid": comment_fqid
        })

        # Send POST request to like the comment
        response = self.client.post(url, {}, format="json")


        # Ensure request was successful
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["action"], "liked")

        # Ensure like is stored in the database
        self.assertEqual(Like.objects.filter(object=self.comment.id).count(), 1)

        # Send another POST request to unlike the comment
        response = self.client.post(url, {}, format="json")

        # Ensure request was successful
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["action"], "unliked")

        # Ensure like is removed from the database
        self.assertEqual(Like.objects.filter(object=self.comment.id).count(), 0)

    def test_get_comment_likes(self):
        """Test retrieving likes for a comment"""

        # Ensure correct IDs are used
        author_id = self.author1.id.split('/')[-1]
        post_id = self.post_id  # Use actual post ID
        post_serial = post_id.split('/')[-1]  # Extracts just the number

        # Create a comment
        self.comment = Comment.objects.create(
            author=self.author2,
            comment="A comment that will be liked.",
            post=post_id
        )
        comment_fqid = self.comment.id.split("/")[-1]  # Extract the comment identifier

        # Create likes in the test database
        Like.objects.create(author=self.author1, object=self.comment.id)
        Like.objects.create(author=self.author2, object=self.comment.id)

        # Construct API URL for retrieving likes 
        url = reverse("social:get_comment_likes", kwargs={
            "author_id": author_id,
            "post_serial": post_serial, 
            "comment_fqid": comment_fqid
        })

        # Send GET request to retrieve likes
        response = self.client.get(url)
        # Ensure request was successful
        self.assertEqual(response.status_code, 200)

        # Ensure correct response type
        self.assertEqual(response.data["type"], "likes")

        # Ensure the correct number of likes is returned
        self.assertEqual(len(response.data["src"]), 2)

        # Ensure the first like is from the correct author
        self.assertEqual(response.data["src"][0]["author"]["id"], self.author1.id)
        self.assertEqual(response.data["src"][1]["author"]["id"], self.author2.id)

    def test_get_specific_comment(self):
        """Test retrieving a specific comment by FQID"""

        # Ensure correct IDs are used
        author_id = self.author1.id.split('/')[-1]
        post_id = self.post_id  # Use actual post ID
        post_serial = post_id.split('/')[-1]  # Extracts just the number

        # Create a comment
        self.comment = Comment.objects.create(
            author=self.author2,
            comment="This is a specific test comment.",
            post=post_id
        )

        # Ensure we use the full FQID stored in the database
        comment_fqid = self.comment.id  

        # Construct API URL for retrieving a specific comment
        url = reverse("social:get_specific_comment", kwargs={
            "author_id": author_id,
            "post_serial": post_serial,
            "remote_comment_fqid": comment_fqid  # Use the **full** comment ID
        })

        # Send GET request to retrieve the specific comment
        response = self.client.get(url)
        # Ensure request was successful
        self.assertEqual(response.status_code, 200)

        # Ensure the comment data matches the expected values
        self.assertEqual(response.data["id"], self.comment.id)
        self.assertEqual(response.data["comment"], "This is a specific test comment.")
        self.assertEqual(response.data["author"]["id"], self.author2.id)

    def test_get_post_likes(self):
        """Test retrieving likes for a post"""

        # Extract author ID
        author_id = self.author1.id.split('/')[-1]

        # Use `localhost:8000` to match real API behavior
        post_url = f"http://localhost:8000/social/api/authors/{author_id}/posts/1"

        # Debugging: Ensure correct post URL
        print("Constructed Post URL:", post_url)

        # Ensure the post exists in the database before proceeding
        print("Post exists in DB before like:", Post.objects.filter(id=post_url).exists())

        # Create likes in the test database using the correct post_url
        Like.objects.create(author=self.author1, object=post_url)
        Like.objects.create(author=self.author2, object=post_url)

        # Construct API URL for retrieving likes
        url = reverse("social:get_post_likes", kwargs={
            "author_id": author_id,
            "post_id": "1"
        })

        # Force Django test client to use `localhost:8000`
        response = self.client.get(url, HTTP_HOST="localhost:8000")

        # Ensure request was successful
        self.assertEqual(response.status_code, 200)

        # Ensure correct response type
        self.assertEqual(response.data["type"], "likes")

        # Ensure the correct number of likes is returned
        self.assertEqual(len(response.data["src"]), 2)

        # Ensure the likes are ordered by `published`
        returned_likes = response.data["src"]
        returned_authors = [like["author"]["id"] for like in returned_likes]

        expected_authors = sorted([self.author1.id, self.author2.id])  # Ensure sorted order
        self.assertEqual(sorted(returned_authors), expected_authors)

    def test_get_liked_by_author_fqid(self):
        """Test retrieving all things liked by an author using FQID"""

        # Use the correct author FQID format
        author_fqid = self.author1.id  # Use the exact author ID stored in DB

        # Construct API URL for retrieving likes by author
        url = reverse("social:get_liked_by_author_fqid", kwargs={"author_fqid": author_fqid})

        # Construct post and comment URLs
        post_url = f"http://localhost:8000/social/api/authors/1/posts/1"
        comment_url = f"http://localhost:8000/social/api/authors/2/commented/12345"

        # Ensure the author exists before proceeding
        print("Author exists in DB before like:", Author.objects.filter(id=author_fqid).exists())

        # Create likes in the test database
        Like.objects.create(author=self.author1, object=post_url)
        Like.objects.create(author=self.author1, object=comment_url)

        # **Override HTTP_HOST to ensure request matches database values**
        response = self.client.get(url, HTTP_HOST="localhost:8000")

        # Ensure request was successful
        self.assertEqual(response.status_code, 200)

        # Ensure correct response type
        self.assertEqual(response.data["type"], "liked")

        # Ensure the correct number of likes is returned
        self.assertEqual(len(response.data["items"]), 2)

        # Ensure the liked items are correct
        returned_likes = response.data["items"]
        returned_objects = [like["object"] for like in returned_likes]

        expected_objects = sorted([post_url, comment_url])  # Ensure sorted order
        self.assertEqual(sorted(returned_objects), expected_objects)


    def test_get_single_like(self):
        """Test retrieving a specific like by FQID"""

        # Ensure correct IDs are used
        author_id = self.author1.id.split('/')[-1]

        # Construct API URL for retrieving a single like
        url = reverse("social:get_single_like", kwargs={"author_id": author_id, "like_serial": "12345"})

        # Construct post URL
        post_url = f"http://localhost:8000/social/api/authors/{author_id}/posts/1"

        # Create a like in the test database
        like = Like.objects.create(
            id=f"http://localhost:8000/social/api/authors/{author_id}/liked/12345",
            author=self.author1,
            object=post_url
        )

        # Send GET request to retrieve the specific like
        response = self.client.get(url, HTTP_HOST="localhost:8000")

        # Ensure request was successful
        self.assertEqual(response.status_code, 200)

        # Ensure the like data matches the expected values
        self.assertEqual(response.data["id"], like.id)
        self.assertEqual(response.data["object"], post_url)
        self.assertEqual(response.data["author"]["id"], self.author1.id)

    def test_get_like_by_fqid(self):
        """Test retrieving a specific like by Fully Qualified ID (FQID)"""

        # Ensure correct IDs are used
        author_id = self.author1.id.split('/')[-1]

        # Construct the expected Like ID format
        like_fqid = f"http://localhost:8000/social/api/authors/{author_id}/liked/abc123"

        # Construct post URL
        post_url = f"http://localhost:8000/social/api/authors/{author_id}/posts/1"

        # Create a like in the test database
        like = Like.objects.create(
            id=like_fqid,
            author=self.author1,
            object=post_url
        )

        # Construct API URL for retrieving the specific like by FQID
        url = reverse("social:get_like_by_fqid", kwargs={"like_fqid": like_fqid})

        # Send GET request to retrieve the specific like
        response = self.client.get(url, HTTP_HOST="localhost:8000")


        # Ensure request was successful
        self.assertEqual(response.status_code, 200)

        # Ensure the like data matches the expected values
        self.assertEqual(response.data["id"], like.id)
        self.assertEqual(response.data["object"], post_url)
        self.assertEqual(response.data["author"]["id"], self.author1.id)
