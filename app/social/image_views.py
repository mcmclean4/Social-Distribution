from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView 
from rest_framework.permissions import AllowAny
from .serializers import PostSerializer, AuthorSerializer
from .models import Post, Author, Follow, FollowRequest,Inbox
import requests
from django.shortcuts import render, redirect, get_object_or_404
from .forms import PostForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.views import View
from django.contrib import messages
from urllib.parse import unquote
from django.db import transaction
from django.conf import settings
import json


@api_view(['GET'])
def getImage(request, internal_id):
    print(request)
    print(internal_id)
    post = get_object_or_404(Post, internal_id=internal_id)
    print(post['image'])

    #return Response(status=200)
    return render(request, 'social/post_detail.html', {'post': post})

