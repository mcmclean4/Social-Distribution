from rest_framework import serializers
from .models import Post

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['auto_id', 'title', 'description', 'contentType', 'content', 'image', 'author', 'published', 'visibility']
