import json
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from social.models import Author, Post, Comment, Like, Node
from django.conf import settings
import base64

class CommentsLikesAPITests(TestCase):
    def setUp(self):
        # settings.HOST = "http://localhost:8000/social/api/"
        settings.HOST = "http://localhost:8000/social/api/"
        
        # Create test users
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")

        # Create test authors
        self.author1 = Author.objects.create(user=self.user1, id=f"http://localhost:8000/social/api/authors/1", displayName="Lara Croft", host=settings.HOST)
        print("author 1 id:")
        print(self.author1.id)
        self.author2 = Author.objects.create(user=self.user2, id=f"http://localhost:8000/social/api/authors/2", displayName="Greg Johnson", host=settings.HOST)

        # Extract author ID
        author_id = self.author1.id.split('/')[-1]

        self.post = Post.objects.create(
            author=self.author1,
            title="Test Post",
            content="This is a test post.",
            id= "http://localhost:8000/social/api/authors/1/posts/1",
            page="http://localhost:8000/social/post/1"
        )
        
        # Refresh to get the posttid
        self.post.refresh_from_db()
        self.post_id = self.post.id  # Store the actual ID assigned
        print(self.post.id)
        print(f"POST PAGE: {self.post.page}")


        # Initialize API client
        self.client = APIClient()
        self.client.force_login(self.user2)
        self.client.defaults['HTTP_HOST'] = 'localhost:8000'

        self.node = Node.objects.create(name="TestNode", base_url=settings.HOST, auth_username="testNodeUsername", auth_password="testNodePassword")

    def test_add_comment(self):
        """Test adding a comment to a post"""
        
        # Extract author ID to match post format
        author_id = self.author1.id.split('/')[-1]
        post_id = self.post_id
        post_serial = post_id.split('/')[-1]
        
        # Construct API URL
        url = reverse("social:post_comments", kwargs={
            "author_id": author_id, 
            "post_serial": post_serial
        })
        
        # Include complete data with the author object
        data = {
            "type": "comment",
            "comment": "This is a new test comment.",
            "contentType": "text/plain",
            "author": {
                "type": "author",
                "id": self.author2.id,
                "host": self.author2.host,
                "displayName": self.author2.displayName
            },
            "post": self.post.id
            # "postFqid": self.post.id
        }
        
        # Make request with the correct data
        response = self.client.post(
            url,
            data=data,
            format="json",
            HTTP_HOST="None"
        )
        # localhost:8000"
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.content}")
        
        # Test assertions
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["comment"], "This is a new test comment.")
        
        # Verify the comment is in the database
        self.assertEqual(Comment.objects.filter(post=post_id).count(), 1)

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

        
        print(f"Verified likes from authors: {self.author1.displayName}, {self.author2.displayName}")
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





class CommentsLikesFunctionTests(TestCase):
    def setUp(self):
        # settings.HOST = "http://localhost:8000/social/api/"
        settings.HOST = "http://localhost:8000/social/api/"
        
        # Create test users
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")

        # Create test authors
        self.author1 = Author.objects.create(user=self.user1, id=f"http://localhost:8000/social/api/authors/1", displayName="Lara Croft", host=settings.HOST)
        print("author 1 id:")
        print(self.author1.id)
        self.author2 = Author.objects.create(user=self.user2, id=f"http://localhost:8000/social/api/authors/2", displayName="Greg Johnson", host=settings.HOST)

        # Extract author ID
        author_id = self.author1.id.split('/')[-1]

        self.post = Post.objects.create(
            author=self.author1,
            title="Test Post",
            content="This is a test post.",
            id= "http://localhost:8000/social/api/authors/1/posts/1",
            page="http://localhost:8000/social/post/1"
        )
        
        # Refresh to get the posttid
        self.post.refresh_from_db()
        self.post_id = self.post.id  # Store the actual ID assigned
        print(self.post.id)
        print(f"POST PAGE: {self.post.page}")


        # Initialize API client
        self.client = APIClient()
        self.client.force_login(self.user2)
        self.client.defaults['HTTP_HOST'] = 'localhost:8000'

        self.node = Node.objects.create(name="TestNode", base_url=settings.HOST, auth_username="testNodeUsername", auth_password="testNodePassword")

    def test_add_comment_func(self):
        """Test retrieving comments for a post (bypassing the API)"""
        
        # Create comments directly
        Comment.objects.create(
            author=self.author2,
            comment="First test comment.",
            post=self.post_id
        )
        
        Comment.objects.create(
            author=self.author1,
            comment="Second test comment.",
            post=self.post_id
        )
        
        # Verify comments exist in the database
        comments = Comment.objects.filter(post=self.post_id).order_by('-published')
        self.assertEqual(comments.count(), 2)
        
        # Verify the order and content (latest first)
        self.assertEqual(comments[0].comment, "Second test comment.")
        self.assertEqual(comments[1].comment, "First test comment.")
        
        # Verify the comment authors
        self.assertEqual(comments[0].author, self.author1)
        self.assertEqual(comments[1].author, self.author2)
        
        # Print for verification
        print(f"Successfully verified {comments.count()} comments")
        print(f"First comment: '{comments[0].comment}' by {comments[0].author.displayName}")
        print(f"Second comment: '{comments[1].comment}' by {comments[1].author.displayName}")

    def test_like_comment_func(self):
        """Test liking and unliking a comment (bypassing API)"""

        # Create a comment in the test database
        comment = Comment.objects.create(
            author=self.author2,
            comment="A comment to like.",
            post=self.post_id
        )
        
        # Verify the comment was created successfully
        self.assertIsNotNone(comment.id)
        print(f"Created comment with ID: {comment.id}")
        
        # Test liking the comment - directly create the Like object
        like = Like.objects.create(
            author=self.author1,
            object=comment.id
        )
        
        # Verify the like was created
        self.assertIsNotNone(like.id)
        print(f"Created like with ID: {like.id}")
        
        # Ensure like is stored in the database
        like_count = Like.objects.filter(object=comment.id).count()
        self.assertEqual(like_count, 1)
        print(f"Confirmed {like_count} like in database")
        
        # Test unliking by removing the like
        like.delete()
        
        # Ensure like is removed from the database
        new_like_count = Like.objects.filter(object=comment.id).count()
        self.assertEqual(new_like_count, 0)
        print(f"Confirmed like was removed, now {new_like_count} likes")

    def test_get_comment_likes_func(self):
        """Test retrieving likes for a comment (bypassing API)"""
        
        # Create a comment
        comment = Comment.objects.create(
            author=self.author2,
            comment="A comment that will be liked.",
            post=self.post_id
        )
        print(f"Created comment with ID: {comment.id}")
        
        # Create likes in the test database
        like1 = Like.objects.create(author=self.author1, object=comment.id)
        like2 = Like.objects.create(author=self.author2, object=comment.id)
        
        print(f"Created likes: {like1.id}, {like2.id}")
        
        # Retrieve likes directly from the database
        likes = Like.objects.filter(object=comment.id).order_by('published')
        
        # Ensure the correct number of likes is returned
        self.assertEqual(likes.count(), 2)
        print(f"Found {likes.count()} likes for the comment")
        
        # Ensure the likes are from the correct authors
        self.assertEqual(likes[0].author, self.author1)
        self.assertEqual(likes[1].author, self.author2)
        
        # Additional verification
        like_authors = [like.author.id for like in likes]
        expected_authors = [self.author1.id, self.author2.id]
        self.assertEqual(sorted(like_authors), sorted(expected_authors))

    def test_get_specific_comment_func(self):
        """
        Test retrieving a specific comment directly from the database
        """
        # Create a comment
        comment = Comment.objects.create(
            author=self.author2,
            comment="This is a specific functional test comment.",
            post=self.post_id
        )
        
        # Retrieve the comment from the database
        retrieved_comment = Comment.objects.get(id=comment.id)
        
        # Verify comment details
        self.assertIsNotNone(retrieved_comment)
        print(f"Retrieved comment ID: {retrieved_comment.id}")
        
        # Check comment attributes
        self.assertEqual(retrieved_comment.comment, "This is a specific functional test comment.")
        self.assertEqual(retrieved_comment.author, self.author2)
        self.assertEqual(retrieved_comment.post, self.post_id)
        
        # Additional verification
        all_comments = Comment.objects.filter(post=self.post_id)
        self.assertIn(retrieved_comment, all_comments)
        print(f"Total comments for this post: {all_comments.count()}")

    def test_get_post_likes_func(self):
        """
        Test creating and retrieving likes for a post directly from the database
        """
        # Construct the full post URL
        post_url = f"http://localhost:8000/social/api/authors/1/posts/1"
        
        # Create likes for the post
        like1 = Like.objects.create(
            author=self.author1,
            object=post_url
        )
        
        like2 = Like.objects.create(
            author=self.author2,
            object=post_url
        )
        
        # Retrieve likes for the post
        post_likes = Like.objects.filter(object=post_url)
        
        # Verify likes
        self.assertEqual(post_likes.count(), 2)
        print(f"Retrieved {post_likes.count()} likes for the post")
        
        # Check like details
        retrieved_like_authors = [like.author for like in post_likes]
        self.assertIn(self.author1, retrieved_like_authors)
        self.assertIn(self.author2, retrieved_like_authors)
        
        # Verify like objects
        self.assertEqual(post_likes[0].object, post_url)
        self.assertEqual(post_likes[1].object, post_url)
        
        print("Like authors:")
        for like in post_likes:
            print(f"  - {like.author.displayName}")

    def test_get_liked_by_author_fqid_func(self):
        """
        Test retrieving all items liked by an author directly from the database
        """
        # Construct URLs for different liked objects
        post_url = f"http://localhost:8000/social/api/authors/1/posts/1"
        comment_url = f"http://localhost:8000/social/api/authors/2/commented/12345"
        
        # Create likes by the author
        like1 = Like.objects.create(
            author=self.author1,
            object=post_url
        )
        
        like2 = Like.objects.create(
            author=self.author1,
            object=comment_url
        )
        
        # Retrieve likes by the author
        author_likes = Like.objects.filter(author=self.author1)
        
        # Verify likes
        self.assertEqual(author_likes.count(), 2)
        print(f"Retrieved {author_likes.count()} likes by the author")
        
        # Check liked objects
        liked_objects = [like.object for like in author_likes]
        self.assertIn(post_url, liked_objects)
        self.assertIn(comment_url, liked_objects)
        
        # Verify each like's details
        for like in author_likes:
            self.assertEqual(like.author, self.author1)
            print(f"Liked object: {like.object}")
        
        # Optional: Verify order of likes (if needed)
        ordered_likes = Like.objects.filter(author=self.author1).order_by('published')
        self.assertEqual(ordered_likes.count(), 2)    
    
    def test_get_single_like_func(self):
        """
        Test retrieving a specific like directly from the database
        """
        # Construct post URL
        author_id = self.author1.id.split('/')[-1]
        post_url = f"http://localhost:8000/social/api/authors/{author_id}/posts/1"

        # Create a like in the test database
        like = Like.objects.create(
            id=f"http://localhost:8000/social/api/authors/{author_id}/liked/12345",
            author=self.author1,
            object=post_url
        )

        # Retrieve the like from the database
        try:
            retrieved_like = Like.objects.get(id=like.id)
            
            # Verify like details
            self.assertIsNotNone(retrieved_like)
            print(f"Retrieved like ID: {retrieved_like.id}")
            
            # Check like attributes
            self.assertEqual(retrieved_like.author, self.author1)
            self.assertEqual(retrieved_like.object, post_url)
            
            # Additional verification
            all_likes = Like.objects.filter(author=self.author1)
            self.assertIn(retrieved_like, all_likes)
            print(f"Total likes by this author: {all_likes.count()}")
            
        except Like.DoesNotExist:
            self.fail(f"Like with ID {like.id} not found in the database")
    def test_get_like_by_fqid_func(self):
        """
        Test retrieving a specific like by Fully Qualified ID directly from the database
        """
        # Construct post URL
        author_id = self.author1.id.split('/')[-1]
        post_url = f"http://localhost:8000/social/api/authors/{author_id}/posts/1"

        # Construct the like FQID
        like_fqid = f"http://localhost:8000/social/api/authors/{author_id}/liked/abc123"

        # Create a like in the test database
        like = Like.objects.create(
            id=like_fqid,
            author=self.author1,
            object=post_url
        )

        # Retrieve the like from the database
        try:
            retrieved_like = Like.objects.get(id=like_fqid)
            
            # Verify like details
            self.assertIsNotNone(retrieved_like)
            print(f"Retrieved like FQID: {retrieved_like.id}")
            
            # Check like attributes
            self.assertEqual(retrieved_like.author, self.author1)
            self.assertEqual(retrieved_like.object, post_url)
            
            # Verify the specific FQID matches
            self.assertEqual(retrieved_like.id, like_fqid)
            
            # Additional verification
            likes_by_author = Like.objects.filter(author=self.author1)
            self.assertIn(retrieved_like, likes_by_author)
            print(f"Total likes by this author: {likes_by_author.count()}")
            
        except Like.DoesNotExist:
            self.fail(f"Like with FQID {like_fqid} not found in the database")