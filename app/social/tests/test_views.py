from .test_setup import TestSetUp

class TestViews(TestSetUp):
    '''
    Posting 6. Successfully create a plain text post
    '''
    def testCreatePlaintextPost(self):
        response = self.client.post(
            self.posts_url, self.post_data, format="json")
        self.assertEqual(response.status_code, 201)