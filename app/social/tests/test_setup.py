from rest_framework.test import APIClient
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from social.models import Author
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
        self.user = User.objects.create_user(username="test_user", password="password")
        

        self.setUpIdentity()
        self.setUpReading()

        # ** EVERYTHING BELOW WAS MADE FOR TEST_POSTING.PY **
        # So may or may not need everything for other test files.

        # urls of endpoints from urls.py
        self.posts_url = reverse('social:post_list_create')
        # inlcude auto_id argument for paths with variable
        self.post_update_url = lambda author_serial, post_serial: reverse('social:update_post', kwargs={'id': author_serial, 'internal_id': post_serial})
        self.post_general_url = lambda author_serial, post_serial: reverse('social:get_author_and_post', kwargs={'author_id': author_serial, 'internal_id': post_serial})
        self.post_detail_url = lambda internal_id: reverse('social:post_detail', kwargs={'internal_id': internal_id})
        self.post_delete_url = lambda post_id: reverse('social:delete_post', kwargs={'auto_id': post_id})
        self.post_create_url = reverse('social:create_post')

        #debug
        print("Existing authors before creating new one:")
        for author in Author.objects.all():
            print(author.id, author.user_id)
        
        # Create an Author instance in the test database
        self.author = Author.objects.create(
            user=self.user,
            id=f"http://localhost:8000/social/api/authors/99",
            host="http://localhost:8000/social/api/",
            displayName="Test Author"
        )


        self.author.refresh_from_db()
        self.user.author = self.author
        self.author.save()

        # Authenticate the test client
        self.client = APIClient()
        self.client.force_login(self.user)

        # hardcoding 1 in .../authors/{author_serial}/posts/{1} for consistency, this post should always be the author's first post
        print(self.author.id)
        parts = self.author.id.split('/')
        author_serial = int(parts[-1])
        print(author_serial)
        # Data for a plain text post
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
                "id": f"http://localhost:8000/social/api/authors/{author_serial}",
                "displayName": self.author.displayName,
                "github": self.author.github,
                "profileImage": "http://localhost:8000/static/images/pfp.jpg",
                "page": f"http://localhost:8000/social/authors/{author_serial}",
                "isAdmin": self.author.isAdmin
            },
            "published": "2015-03-09T13:07:04+00:00",
            "visibility": "PUBLIC",
            "likes": [],
            "comments": []
        }

        # data for a CommonMark post
        self.markdown_post_data = {
            "type": "post",
            "title": "A different title for the markdown post",
            "id":f"http://localhost:8000/social/api/authors/{author_serial}/posts/{1}",
            "page": self.author.page,
            "description":"This post discusses stuff -- brief",
            "contentType": "text/markdown",
            "content": "# Header **bold text**",
            "author": {
                "type": self.author.type,
                "id": f"http://localhost:8000/social/api/authors/{author_serial}",
                "displayName": self.author.displayName,
                "github": self.author.github,
                "profileImage": "http://localhost:8000/static/images/pfp.jpg",
                "page": f"http://localhost:8000/social/authors/{author_serial}",
                "isAdmin": self.author.isAdmin
            },
            "published": "2015-03-09T13:07:04+00:00",
            "visibility": "PUBLIC",
            "likes": [],
            "comments": []
        }
        
        # Create a test image in memory
        self.image = self.generate_test_image()
        # data for a post with an image
        author_json_string = json.dumps(AuthorSerializer(self.author).data)
        self.image_post_data = {
            "type": "post",
            "title":"A post title about a post about web dev",
            "id":f"http://localhost:8000/social/api/authors/{author_serial}/posts/{1}",
            "page": self.author.page,
            "title":"A post title about a post about web dev",
            "description":"This post discusses stuff -- brief",
            "contentType": "image/png;base64",
            "content": "placeholder content",
            "image": self.image,
            "author": AuthorSerializer(self.author).data,
            "published": "2015-03-09T13:07:04+00:00",
            "visibility": "PUBLIC",
            "likes": [],
            "comments": []
        }
        
        return super().setUp()
    

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
            "displayName": "test_displayName"
        }

        self.register_data_2 = {
            "username":"test_username2",
            "password": "password2",
            "displayName": "test_displayName2"
        }


    def setUpReading(self):
        self.stream_url = reverse('social:index')
        

    def tearDown(self):
        print("Cleaning up test data...")
        return super().tearDown()
    

    def generate_test_image(self):
        # Generates a simple test png image
        image = io.BytesIO()
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))  # Create a red image
        img.save(image, format="PNG")
        image.seek(0)
        return SimpleUploadedFile("test_image.png", image.getvalue(), content_type="image/png")
    