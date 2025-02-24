
from .test_setup import TestSetUp
from social.models import Post

class TestPosting(TestSetUp):
    '''
    Add these lines before the assertions, and write response.data into terminal after running for debugging
    import pdb
    pdb.set_trace()
    '''

    '''
    Posting 1 & 6. Successfully create a plain text post
    '''
    def testCreatePlaintextPost(self):
        # Create post
        response = self.client.post(
            self.posts_url, self.plaintext_post_data, format="json")
        # Check response status code and data fields are same as the post that we created
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['contentType'], self.plaintext_post_data['contentType'])
        self.assertEqual(response.data['content'], self.plaintext_post_data['content'])

    
    

    
    


