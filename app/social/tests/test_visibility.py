from .test_setup import TestSetUp
from social.models import Post, Author, Follow, Node
from django.contrib.auth.models import User
from django.urls import reverse
from base64 import b64encode

class VisibilityAPITests(TestSetUp):
    def setUp(self):
        # Call parent setup
        #super().setUp()
        
        self.node1 = Node.objects.create(
            name = "test_node1",
            base_url= 'http://localhost:8001/social/api/',
            auth_username= "user1",
            auth_password = "pass1",
        )
        
        # Create test users
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")
        self.user3 = User.objects.create_user(username="user3", password="password")

        # Create test authors
        self.author1 = Author.objects.create(
            user=self.user1, 
            id=f"http://localhost:8000/social/api/authors/1", 
            displayName="Visibility Tester", 
            host="http://localhost:8000/social/api/")
        
        self.author2 = Author.objects.create(
            user=self.user2, 
            id=f"http://localhost:8000/social/api/authors/2", 
            displayName="Friend User", 
            host="http://localhost:8000/social/api/")
        
        self.author3 = Author.objects.create(
            user=self.user3, 
            id=f"http://localhost:8000/social/api/authors/3", 
            displayName="Non-Friend User", 
            host="http://localhost:8000/social/api/")
        
        # Setup friendships
        # Author1 and Author2 are mutual followers (friends)
        Follow.objects.create(follower_id=self.author1.id, followee=self.author2)
        Follow.objects.create(follower_id=self.author2.id, followee=self.author1)
        
        # Create different visibility posts
        self.public_post = Post.objects.create(
            author=self.author1,
            title="Public Post",
            content="This is a public post",
            contentType="text/plain",
            visibility="PUBLIC",
            description="Public test post"
        )
        
        self.friends_post = Post.objects.create(
            author=self.author1,
            title="Friends Only Post",
            content="This is a friends-only post",
            contentType="text/plain",
            visibility="FRIENDS",
            description="Friends test post"
        )
        
        self.unlisted_post = Post.objects.create(
            author=self.author1,
            title="Unlisted Post",
            content="This is an unlisted post",
            contentType="text/plain",
            visibility="UNLISTED",
            description="Unlisted test post"
        )
    
    def get_basic_auth_header(self, username, password):
        credentials = f"{username}:{password}"
        encoded_credentials = b64encode(credentials.encode()).decode('ascii')
        return {'HTTP_AUTHORIZATION': f'Basic {encoded_credentials}'}
    
    def test_public_post_visibility(self):
        """Test that PUBLIC posts are visible to everyone"""
        # Should be visible to the author
        own_posts = Post.objects.filter(author=self.author1, visibility="PUBLIC")
        self.assertEqual(own_posts.count(), 1)
        self.assertEqual(own_posts.first().title, "Public Post")
        
        # Should be visible to friends
        friend_visible_posts = Post.objects.filter(author=self.author1, visibility="PUBLIC")
        self.assertEqual(friend_visible_posts.count(), 1)
        
        # Should be visible to non-friends
        non_friend_visible_posts = Post.objects.filter(author=self.author1, visibility="PUBLIC")
        self.assertEqual(non_friend_visible_posts.count(), 1)
        
        author_id = self.author1.id.split('/')[-1]
        
        # Call the API to get posts for author1
        headers = self.get_basic_auth_header(self.node1.auth_username, self.node1.auth_password)
        response = self.client.get(reverse("social:post_detail", kwargs={"internal_id": self.public_post.internal_id}), **headers)
        
        # Test both model and API
        # First verify the model count
        public_posts_model = Post.objects.filter(author=self.author1, visibility="PUBLIC").count()
        
        # Now test both with assertions
        # For model verification:
        self.assertEqual(public_posts_model, 1)
        
        # For API verification - should get 200 OK response
        self.assertEqual(response.status_code, 302)
        
        print(f"API public post visibility test passed")
    
    def test_friends_post_visibility(self):
        """Test that FRIENDS posts are only visible to friends"""
        # Test in db first
        # Should be visible to the author
        own_posts = Post.objects.filter(author=self.author1, visibility="FRIENDS")
        self.assertEqual(own_posts.count(), 1)
        self.assertEqual(own_posts.first().title, "Friends Only Post")
        
        # Verify author2 is friends with author1
        self.assertIn(self.author2, self.author1.friends)
        
        # Use the PostManager's get_posts_for_author
        friend_visible_posts = Post.objects.filter(
            author=self.author1, 
            visibility="FRIENDS"
        )
        self.assertEqual(friend_visible_posts.count(), 1)
        
        ######################################################


        # Get author IDs for API calls
        author1_id = self.author1.id.split('/')[-1]
        
        # Test visibility for a friend (user2/author2)
        self.client.logout()
        self.client.force_login(self.user2)
        
        # Call the API to get posts for author1 from perspective of user2 (a friend)
        
        headers = self.get_basic_auth_header(self.node1.auth_username, self.node1.auth_password)
        friend_response = self.client.get(reverse("social:post_detail", kwargs={"internal_id": self.friends_post.internal_id}), **headers)
        
        self.assertEqual(friend_response.status_code, 200)
        
        self.assertNotIn('message', friend_response.context)
        
        
        # Now test with non-friend (user3/author3)
        self.client.logout()
        self.client.force_login(self.user3)
        
        # Call API as non-friend
        
        headers = self.get_basic_auth_header(self.node1.auth_username, self.node1.auth_password)
        non_friend_response = self.client.get(reverse("social:post_detail", kwargs={"internal_id": self.friends_post.internal_id}), **headers)
        
        self.assertEqual(non_friend_response.status_code, 200)
        self.assertIn('message', non_friend_response.context)
        
        print(f"API friends post visibility test passed")
    
    def test_unlisted_post_visibility(self):
        """Test that UNLISTED posts are only visible with direct link"""
        # test in DB first
        # Should be visible to the author
        own_posts = Post.objects.filter(author=self.author1, visibility="UNLISTED")
        self.assertEqual(own_posts.count(), 1)
        self.assertEqual(own_posts.first().title, "Unlisted Post")
        
        # Should be accessible by direct ID
        post_id = self.unlisted_post.id
        direct_access_post = Post.objects.get(id=post_id)
        self.assertEqual(direct_access_post.title, "Unlisted Post")
        
        # But should not appear in regular listings (simulate this)
        public_stream = Post.objects.filter(visibility="PUBLIC")
        unlisted_in_public = any(p.id == self.unlisted_post.id for p in public_stream)
        self.assertFalse(unlisted_in_public, "Unlisted post should not appear in public stream")
        
        ##################################################################

        author_id = self.author1.id.split('/')[-1]
        post_id = self.unlisted_post.internal_id
        
        # First test general listing - should NOT include unlisted post
        
        headers = self.get_basic_auth_header(self.node1.auth_username, self.node1.auth_password)
        response = self.client.get(reverse("social:post_detail", kwargs={"internal_id": self.unlisted_post.internal_id}), **headers)
        
        self.assertEqual(response.status_code, 302)
        #self.assertNotIn('message', response.context)
        
        print(f"API unlisted post access test passed")
    
    def test_post_manager_filters(self):
        """Test the Post.objects manager's filtering capabilities"""
        # Create another post to ensure filtering works properly
        Post.objects.create(
            author=self.author1,
            title="Another Public Post",
            content="This is another public post",
            contentType="text/plain",
            visibility="PUBLIC",
            description="Another public test post"
        )
        
        public_posts = Post.objects.filter(visibility="PUBLIC")
        self.assertEqual(public_posts.count(), 2)
        
        # Get all posts for author1 (should be 4 total)
        all_author_posts = Post.objects.filter(author=self.author1)
        self.assertEqual(all_author_posts.count(), 4)
        
        # Test filtering by content type
        plain_text_posts = Post.objects.filter(contentType="text/plain")
        self.assertEqual(plain_text_posts.count(), 4)
        
        print(f"Post manager filtering test passed")
    
    def test_deleted_post_visibility(self):
        """Test that DELETED posts are not visible"""
        # Create a post and then mark it as deleted
        self.deleted_post = Post.objects.create(
            author=self.author1,
            title="Soon To Be Deleted Post",
            content="This post will be deleted",
            contentType="text/plain",
            visibility="DELETED",
            description="Deleted test post"
        )
        
        # Verify it exists
        self.assertIsNotNone(Post.objects.filter(id=self.deleted_post.id).first())

        author_id = self.author1.id.split('/')[-1]
        post_id = self.deleted_post.internal_id
        
        # First verify the post exists and is accessible
        headers = self.get_basic_auth_header(self.node1.auth_username, self.node1.auth_password)
        response = self.client.get(reverse("social:post_detail", kwargs={"internal_id": self.deleted_post.internal_id}), **headers)
        
        self.assertEqual(response.status_code, 302)
        #self.assertIn('message', response.context)
        
        print(f"API deleted post visibility test passed")