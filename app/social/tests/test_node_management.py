from .test_setup import TestSetUp
from unittest import mock
from django.test import TestCase, Client
from django.urls import reverse
from social.models import Node
from requests import get
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
            auth_password = "pass1",
        )
        
        self.node2 = Node.objects.create(
            name = "test_node2",
            base_url= 'http://localhost:8002/social/api/',
            auth_username= "user2",
            auth_password = "pass2"
        )
        
        self.node3 = Node.objects.create(
            name = "test_node3",
            base_url= 'http://localhost:8003/social/api/',
            auth_username= "user3",
            auth_password = "pass3"
        )
    
    def get_basic_auth_header(self, username, password):
        credentials = f"{username}:{password}"
        encoded_credentials = b64encode(credentials.encode()).decode('ascii')
        return {'HTTP_AUTHORIZATION': f'Basic {encoded_credentials}'}
        
    def test_node_to_node_communication(self):
        #Node2 sends a request with its own valid credentials
        headers = self.get_basic_auth_header(self.node2.auth_username, self.node2.auth_password)
        response = self.client.get(reverse('social:get_authors'), **headers)
        self.assertEqual(response.status_code, 200)

        #Node1 sends a request with its own valid credentials
        headers = self.get_basic_auth_header(self.node1.auth_username, self.node1.auth_password)
        response = self.client.get(reverse('social:get_authors'), **headers)
        self.assertEqual(response.status_code, 200)

        #Node1 sends request with invalid password
        headers = self.get_basic_auth_header(self.node1.auth_username, "invalidpassword")
        response = self.client.get(reverse('social:get_authors'), **headers)
        self.assertEqual(response.status_code, 403)

        #Unknown credentials
        headers = self.get_basic_auth_header("fakeuser", "fakepass")
        response = self.client.get(reverse('social:get_authors'), **headers)
        self.assertEqual(response.status_code, 403)
        
    #Test for disabling Nodes
    def test_node_disabling(self):
        # Disable node2
        self.node2.enabled = False
        self.node2.save()

        # Attempt to authenticate using disabled node's credentials
        credentials = f"{self.node2.auth_username}:{self.node2.auth_password}"
        encoded_credentials = b64encode(credentials.encode()).decode('ascii')
        headers = {'HTTP_AUTHORIZATION': f'Basic {encoded_credentials}'}

        response = self.client.get(reverse('social:get_authors'), **headers)

        print(response.data)
        self.assertEqual(response.status_code, 403)
        
        
        def testNodeManagement(self):
            self.assertEqual(1, 1)
    
    def test_deleted_node_cannot_authenticate(self):
        #Make sure node3 works
        headers = self.get_basic_auth_header(self.node3.auth_username, self.node3.auth_password)
        response = self.client.get(reverse('social:get_authors'), **headers)
        self.assertEqual(response.status_code, 200)
        
        # Delete node3
        self.node3.delete()

        # Attempt to authenticate using deleted node3's credentials
        credentials = f"{self.node3.auth_username}:{self.node3.auth_password}"
        encoded_credentials = b64encode(credentials.encode()).decode('ascii')
        headers = {'HTTP_AUTHORIZATION': f'Basic {encoded_credentials}'}

        response = self.client.get(reverse('social:get_authors'), **headers)

        print(response.data)
        self.assertEqual(response.status_code, 403)