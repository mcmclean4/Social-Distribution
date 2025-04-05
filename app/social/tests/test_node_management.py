from .test_setup import TestSetUp
from unittest import mock
from django.test import TestCase, Client
from django.urls import reverse
from social.models import Node
from django.contrib.auth.models import User
from base64 import b64encode
import json

class TestNodeManagement(TestSetUp):
    
    #Test for node to node communication
    def setUp(self):
        self.node1 = Node.objects.create(
            name = "test_node1",
            base_url= 'http://localhost:8001/social/api/',
            auth_username= "user1",
            auth_password = "pass1"
        )
        
        self.node2 = Node.objects.create(
            name = "test_node1",
            base_url= 'http://localhost:8002/social/api/',
            auth_username= "user2",
            auth_password = "pass2"
        )
        
    @mock.patch('social.views.get_authors')
    def test_node_to_node_communication(self, mock_get_authors):
        
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'success',
            'message': 'Message received successfully',
            'node_id': 'node2'
        }
        
        #Test getting authors with the auth
        auth_str = f"{self.node1.auth_username}:{self.node1.auth_password}"
        auth_header = b64encode(auth_str.encode()).decode('ascii')
        headers = {'HTTP_AUTHORIZATION': f'Basic {auth_header}'}
        
        
        
        response = self.client.get(
            reverse('social:get_authors'),
            **headers
        )
        
        print(response.data)
        
        self.assertEqual(response.status_code, 200)
        
        
        #Test getting authors without the auth:
        auth_str = f"{self.node1.auth_username}:invalidPassword"
        auth_header = b64encode(auth_str.encode()).decode('ascii')
        headers = {'HTTP_AUTHORIZATION': f'Basic {auth_header}'}
        
        response = self.client.get(
            reverse('social:get_authors'),
            **headers
        )
        
        self.assertEqual(response.status_code, 403)
        
        
        
        
    #Test for disabling Nodes
    
    # placeholder test
    
    def get_basic_auth_header(self, username, password):
        """
        Helper function to generate the Basic Authentication header value.
        """
        from base64 import b64encode
        credentials = f'{username}:{password}'
        return b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    def testNodeManagement(self):
        self.assertEqual(1, 1)