
from .test_setup import TestSetUp
from social.models import Post
import json

class TestPosting(TestSetUp):
    '''
    Add these lines before the assertions, and write response.data into terminal after running for debugging
    import pdb
    pdb.set_trace()
    '''

    '''
    Posting 1 & 6. Successfully create a plain text post. 
    Tests 'api/posts/' endpoint for creating posts with a POST request
    Tests 'api/authors/<int:author_id>/posts/<int:internal_id>/' endpoint for retreiving posts with a GET request
    '''
    '''
    def test_create_plaintext_post(self):
        # Create a post
        create_response = self.client.post(
            self.posts_url, self.plaintext_post_data, format="json")
        self.assertEqual(create_response.status_code, 201)
        
        # create_response.data['id'] should be "http://localhost:8000/social/api/authors/2/posts/1", parse for serial ids
        parts = create_response.data['id'].split('/')
        author_serial = int(parts[-3])
        post_serial = int(parts[-1]) 

        # Check data fields are same as the post data that we sent
        self.assertEqual(create_response.data['contentType'], self.plaintext_post_data['contentType'])
        self.assertEqual(create_response.data['content'], self.plaintext_post_data['content'])

        # Check we can also retrieve the post, and the data is the same again
        get_response = self.client.get(self.post_general_url(author_serial, post_serial))
        self.assertEqual(get_response.status_code, 200)
        # Remove ['post'] if we change get_author_and_post to only return post
        self.assertEqual(get_response.data['post']['contentType'], self.plaintext_post_data['contentType'])
        self.assertEqual(get_response.data['post']['content'], self.plaintext_post_data['content'])
    '''
    '''
    Posting 3. Successfully update an exisitng post. Tests 'api/authors/<int:id>/posts/<int:internal_id>/update/' endpoint
    '''
    '''
    def test_edit_post(self):
        print("Existing posts before creating:")
        for post in Post.objects.all():
            print(post.id)

        # Create a post
        create_response = self.client.post(
            self.posts_url, self.plaintext_post_data, format="json")
        self.assertEqual(create_response.status_code, 201)
        
        parts = create_response.data['id'].split('/')
        author_serial = int(parts[-3])
        post_serial = int(parts[-1]) 

        # Make changes to some fields
        self.plaintext_post_data['title'] = "An Updated Title"
        self.plaintext_post_data['description'] = "An updated description"
        self.plaintext_post_data['contentType'] = "text/markdown"
        self.plaintext_post_data['content'] = "Updated content"

        print("DEBUG ***************************")
        print(create_response.data['id'])
        print(self.plaintext_post_data['id'])
        print(author_serial)
        print(post_serial)

        print("Existing posts before updating:")
        for post in Post.objects.all():
            print(post.id)

        # Submit the changes with PUT request
        update_response = self.client.put(
            self.post_general_url(author_serial, post_serial), self.plaintext_post_data, format="json")
        print(update_response)
        self.assertEqual(update_response.status_code, 200)

        # Get post from db and check all the updated fields are correct and has kept the same id
        post = Post.objects.get(id=create_response.data['id'])
        self.assertEqual(post.title, self.plaintext_post_data['title'])
        self.assertEqual(post.description, self.plaintext_post_data['description'])
        self.assertEqual(post.contentType, self.plaintext_post_data['contentType'])
        self.assertEqual(post.content, self.plaintext_post_data['content'])
    '''

    '''
    Posting 5. Successfully create a markdown text post
    '''
    '''
    def test_create_markdown_post(self):
        # Create a markdown post
        create_response = self.client.post(
            self.posts_url, self.markdown_post_data, format="json")
        self.assertEqual(create_response.status_code, 201)
        
        # create_response.data['id'] should be "http://localhost:8000/social/api/authors/2/posts/1", parse for serial ids
        parts = create_response.data['id'].split('/')
        author_serial = int(parts[-3])
        post_serial = int(parts[-1]) 

        # Check data fields are same as the post data that we sent
        self.assertEqual(create_response.data['contentType'], self.markdown_post_data['contentType'])
        self.assertEqual(create_response.data['content'], self.markdown_post_data['content'])

        # Check we can also retrieve the post, and the data is the same again
        get_response = self.client.get(self.post_general_url(author_serial, post_serial))
        self.assertEqual(get_response.status_code, 200)
        # Remove ['post'] if we change get_author_and_post to only return post
        self.assertEqual(get_response.data['post']['contentType'], self.markdown_post_data['contentType'])
        self.assertEqual(get_response.data['post']['content'], self.markdown_post_data['content'])
    '''

    '''
    Posting 7. Successfully create an image text post
    '''
    '''
    def test_create_image_post(self):
        print(self.image_post_data['author'])

        create_response = self.client.post(
            self.posts_url, self.image_post_data, format="multipart")
        print(create_response)
        print(create_response.data)
        self.assertEqual(create_response.status_code, 201)

        # create_response.data['id'] should be "http://localhost:8000/social/api/authors/2/posts/1", parse for serial ids
        parts = create_response.data['id'].split('/')
        author_serial = int(parts[-3])
        post_serial = int(parts[-1]) 

        # Check data fields are same as the post data that we sent
        self.assertEqual(create_response.data['contentType'], self.image_post_data['contentType'])
        self.assertEqual(create_response.data['image'], self.image_post_data['image'])
        # Check if image is included in response, and should return as a url
        self.assertIn("image", create_response.data)
        self.assertTrue(create_response.data["image"].startswith("http"))

        # Check we can also retrieve the post, and the data is the same again
        get_response = self.client.get(self.post_general_url(author_serial, post_serial))
        self.assertEqual(get_response.status_code, 200)
        # Remove ['post'] if we change get_author_and_post to only return post
        self.assertEqual(get_response.data['post']['contentType'], self.image_post_data['contentType'])
        self.assertEqual(get_response.data['post']['image'], self.image_post_data['image'])
    '''


    '''
    Posting 9. Successfully delete a post by updating its visibility field
    '''
    
    def test_delete_post(self):
        # Create a post
        create_response = self.client.post(
            self.posts_url, self.plaintext_post_data, format="json")
        print(create_response)
        self.assertEqual(create_response.status_code, 201)
        
        parts = create_response.data['id'].split('/')
        author_serial = int(parts[-3])
        post_serial = int(parts[-1])

        # Submit the changes with a DELETE request
        delete_response = self.client.delete(
            self.post_general_url(author_serial, post_serial), self.plaintext_post_data, format="json")
        print(delete_response)
        self.assertEqual(delete_response.status_code, 204)

        # Get post from db and check all the visibility field is updated
        post = Post.objects.get(id=create_response.data['id'])
        self.assertEqual(post.visibility, "DELETED")

    '''
    Posting 10. Successfully create a post through the web browser
    '''
    def test_create_post_via_browser(self):
        # Visit the create post page
        visit_response = self.client.get(self.post_create_url)
        self.assertEqual(visit_response.status_code, 200)
        self.assertTemplateUsed(visit_response, 'social/create_post.html')

        
        
        # Submit the plaintext post as a form with POST request
        submit_response = self.client.post(self.post_create_url, self.plaintext_post_data, format='json')
        self.assertEqual(submit_response.status_code, 200)

        # Verify that the post was created in the database
        post = Post.objects.first()
        self.assertIsNotNone(post)
        self.assertEqual(post.title, self.plaintext_post_data['title'])
        self.assertEqual(post.content, self.plaintext_post_data['content'])
        self.assertEqual(post.author, self.author)

        


    

    
    


