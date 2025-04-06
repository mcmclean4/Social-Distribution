from rest_framework.test import APIClient
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from social.models import Author, Node
from django.core.files.uploadedfile import SimpleUploadedFile
import io
import os
from PIL import Image 
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import json
from social.serializers import AuthorSerializer
from django.utils.safestring import mark_safe
import base64


# Referenced:
# https://www.youtube.com/watch?v=17KdirMbmHY

from django.test import TestCase, override_settings


 

class TestSetUp(TestCase):
    '''
    re-run app with docker compose build & up
    in another terminal run tests with this command in app/:
    docker exec -it w25-project-mod-cornsilk-social-1 python manage.py test social.tests

    or if you only want to run one of the test files (test_sharing in this example) use:
    docker exec -it w25-project-mod-cornsilk-social-1 python manage.py test social.tests.test_posting


    '''
    def setUp(self):
        User.objects.all().delete()
        Author.objects.all().delete()
        super().tearDown()

        # Create a user for the author
        self.user = User.objects.create_user(username="TestUser", password="password")
        self.node = Node.objects.create(name="TestNode", base_url="http://localhost:8000/social/api/", auth_username="admin9", auth_password="secret9")
        
        # Create an Author instance in the test database
        # Manually set author serial to 99 to avoid collision
        self.author = Author.objects.create(
            user=self.user,
            id=f"http://localhost:8000/social/api/authors/99",
            host="http://localhost:8000/social/api/",
            displayName="Test Author"
        )

        # save the test author
        self.author.refresh_from_db()
        self.user.author = self.author
        self.author.save()

        # Authenticate the test client
        self.client = APIClient()
        self.client.force_login(self.user)

        # Organized creating json objects and urls for different test cases
        self.setUpPosting()
        self.setUpIdentity()
        self.setUpReading()
     
        return super().setUp()
    

    def setUpPosting(self):

        # urls of endpoints from urls.py
        self.posts_url = reverse('social:post_list_create')
        # inlcude auto_id argument for paths with variable
        self.post_update_url = lambda author_serial, post_serial: reverse('social:update_post', kwargs={'id': author_serial, 'internal_id': post_serial})
        self.post_general_url = lambda author_serial, post_serial: reverse('social:get_author_and_post', kwargs={'author_id': author_serial, 'internal_id': post_serial})
        self.post_detail_url = lambda internal_id: reverse('social:post_detail', kwargs={'internal_id': internal_id})
        self.post_delete_url = lambda post_id: reverse('social:delete_post', kwargs={'auto_id': post_id})
        self.post_create_url = reverse('social:create_post')

        # Data for a plain text post for self.author, will be post serial 1
        parts = self.author.id.split('/')
        author_serial = int(parts[-1])
        self.plaintext_post_data = {
            "type": "post",
            "title":"A post title about a post about web dev",
            "id":f"http://localhost:8000/social/api/authors/{author_serial}/posts/{1}",
            "page": self.author.page,
            "title":"A post title about a post about web dev",
            "description":"This post discusses stuff -- brief",
            "contentType": "text/plain",
            "content": "Þā wæs on burgum Bēowulf Scyldinga",
            "author": {
                "type": self.author.type,
                "id": self.author.id,
                "displayName": self.author.displayName,
                "github": self.author.github,
                "profileImage": self.author.profileImage,
                "page": self.author.page,
                "isAdmin": self.author.isAdmin
            },
            "published": "2015-03-09T13:07:04+00:00",
            "visibility": "PUBLIC",
            "likes": [],
            "comments": []
        }
    
        # Data for a markdown post
        self.markdown_post_data = self.plaintext_post_data.copy()
        self.markdown_post_data["title"] = "A different title for the markdown post"
        self.markdown_post_data["contentType"] = "text/markdown"
        self.markdown_post_data["content"] = "# Header **bold text**"

        self.image_post_data = self.plaintext_post_data.copy()
        self.image_post_data["contentType"] = "image/png;base64"
        self.image_post_data["content"] = self.generate_test_image()


    def setUpIdentity(self):

        self.register_url = reverse('social:register')
        self.get_authors_url = reverse('social:get_authors')
        self.get_author_url = lambda author_id: reverse('social:get_author', kwargs={'id' : author_id})
        self.profile_page_url = lambda author_id: reverse('social:profile_page', kwargs={'id' : author_id})
        self.profile_edit_url = lambda author_id: reverse('social:profile_edit', kwargs={'id' : author_id})

        # Set up needed for test_indentity.py
        self.register_data = {
            "username":"test_username",
            "password": "password",
            "displayName": "test_displayName",
            "github": ""
        }

        self.register_data_2 = {
            "username":"test_username2",
            "password": "password2",
            "displayName": "test_displayName2"
        }


    def setUpReading(self):
        self.stream_url = reverse('social:index')


    def generate_test_image(self):
        # Generates a simple test png image, returns as base64 encoded string.
        # Create a BytesIO object to hold the image data
        image = io.BytesIO()
        # Create a simple 100x100 red image
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        # Save the image to the BytesIO object
        img.save(image, format="PNG")
        # Reset the file pointer to the beginning
        image.seek(0)
        # Convert the image data to base64
        image_data = base64.b64encode(image.getvalue()).decode('utf-8')
        # Store the BytesIO object for cleanup in tearDown
        self.test_image_bytes = image
        return image_data
        

    def tearDown(self):
        print("Cleaning up test data...")
        # deletes the generated test image
        if hasattr(self, 'test_image_bytes'):
            print("deleting test img")
            self.test_image_bytes.close()
        return super().tearDown()
    


    