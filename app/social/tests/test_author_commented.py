from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from social.models import Author, Comment, Post
from django.conf import settings


class CommentedAPITests(TestCase):
    def setUp(self):
        settings.HOST = "http://localhost:8000/social/"
        
        # Create test users
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")

        # Create test authors
        self.author1 = Author.objects.create(user=self.user1, displayName="Lara Croft", host=settings.HOST)
        self.author2 = Author.objects.create(user=self.user2, displayName="Greg Johnson", host=settings.HOST)

        # Create a test post
        self.post = Post.objects.create(
            author=self.author1,
            title="Test Post",
            content="This is a test post."
        )

        # Refresh to get the actual ID
        self.post.refresh_from_db()
        self.post_id = self.post.id  

        # Create test comments
        self.comment1 = Comment.objects.create(
            author=self.author1,
            comment="First comment by author1",
            post=self.post_id
        )
        self.comment2 = Comment.objects.create(
            author=self.author1,
            comment="Second comment by author1",
            post=self.post_id
        )

        # Store comment identifiers
        self.comment1.refresh_from_db()
        self.comment2.refresh_from_db()
        self.comment_serial1 = self.comment1.id.split("/")[-1]
        self.comment_fqid1 = self.comment1.id

        # Initialize API client
        self.client = APIClient()
        self.client.force_login(self.user2)

    def test_get_author_comments(self):
        """Test retrieving all comments made by an author using author_id"""
        # For debugging, print the actual author ID and check its format
        print(f"DEBUG: Actual author1.id = {self.author1.id}")
        
        # Check how your model stores IDs
        all_authors = Author.objects.all()
        print("All author IDs in database:")
        for a in all_authors:
            print(f"  - {a.id}")
        
        # Extract the ID part based on your actual author ID format
        author_id = self.author1.id.split("/")[-1]
        url = reverse("social:get_author_comments", kwargs={"author_id": author_id})
        
        response = self.client.get(url,HTTP_HOST="localhost:8000")
        
        self.assertEqual(response.status_code, 200)
        # Rest of assertions...
        
        # Check response format - if it's a list:
        if isinstance(response.data, list):
            self.assertEqual(len(response.data), 2)
        # If it's a dictionary with 'type' and 'comments':
        else:
            self.assertEqual(response.data["type"], "comments")
            self.assertEqual(len(response.data["comments"]), 2)

    def test_get_author_comments_by_fqid(self):
        """Test retrieving all comments made by an author using author_fqid"""
        author_fqid = self.author1.id
        url = reverse("social:get_author_comments_by_fqid", kwargs={"author_fqid": author_fqid})

        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)

        # If response is a list, handle it appropriately
        if isinstance(response.data, list):  
            self.assertGreaterEqual(len(response.data), 2)
            
            # Find each comment by its content, rather than relying on order
            comments_text = [item["comment"] for item in response.data]
            self.assertIn("First comment by author1", comments_text)
            self.assertIn("Second comment by author1", comments_text)
        else:
            self.assertEqual(response.data["type"], "comments")
            self.assertEqual(len(response.data["comments"]), 2)
            
            # Find each comment by its content, rather than relying on order
            comments_text = [item["comment"] for item in response.data["comments"]]
            self.assertIn("First comment by author1", comments_text)
            self.assertIn("Second comment by author1", comments_text)

    def test_get_specific_comment_by_serial(self):
        """Test retrieving a specific comment using its serial number"""
        author_id = self.author1.id.split('/')[-1]
        url = reverse("social:get_specific_comment_by_serial", kwargs={
            "author_id": author_id, 
            "comment_serial": self.comment_serial1
        })

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.comment1.id)
        self.assertEqual(response.data["comment"], "First comment by author1")

    def test_get_comment_by_fqid(self):
        """Test retrieving a specific comment using its fully qualified ID"""
        url = reverse("social:get_comment_by_fqid", kwargs={"comment_fqid": self.comment_fqid1})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.comment1.id)
        self.assertEqual(response.data["comment"], "First comment by author1")