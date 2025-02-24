
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
    def testCreatePlaintextPost(self):
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
    def testEditPost(self):
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

        # Submit the changes as a form with PUT request
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
    
    
    

    
    


