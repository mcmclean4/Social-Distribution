from rest_framework import serializers
from .models import Post, Author, User


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['title', 'description', 'contentType', 'content',
                  'image', 'author', 'published', 'visibility']


class AuthorSerializer(serializers.Serializer):
    user = User
    type = serializers.CharField(required=True)
    id = serializers.URLField(required=True)
    # host = serializers.URLField(required=True)
    displayName = serializers.CharField(required=True)
    github = serializers.URLField()
    profileImage = serializers.URLField()
    page = serializers.URLField()
    isAdmin = serializers.BooleanField()

    def create(self, validated_data):
        return Author.objects.create(**validated_data)

    def edit(self, validated_data):
        pass
