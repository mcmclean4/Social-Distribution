from .test_setup import TestSetUp
from social.models import Post

class TestSharing(TestSetUp):

    '''
    Sharing 1. Successfully get a link for a post 
    '''
    def test_link(self):
        # Create first post
        create_response = self.client.post(
            self.posts_url, self.plaintext_post_data, format="json")
        self.assertEqual(create_response.status_code, 201)
        
        post = Post.objects.get(id=create_response.data['id'])
        internal_id = post.__dict__['internal_id']

        # Visit /social/post/1/, the link we'd get from clicking on a post from the stream
        get_response = self.client.get(
            self.post_detail_url(internal_id)
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertTemplateUsed(get_response, 'social/post_detail.html')
        # Check detail page displays post's data
        self.assertContains(get_response,  self.plaintext_post_data['title'])
        self.assertContains(get_response,  self.plaintext_post_data['content'])
