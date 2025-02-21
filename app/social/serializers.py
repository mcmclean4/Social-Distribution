from rest_framework import serializers
from .models import Post, Author, User

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


class CommentSerializer(serializers.Serializer):
    id = serializers.URLField()
    author = AuthorSerializer()
    comment = serializers.CharField()
    contentType = serializers.CharField()
    published = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S%z")
    post = serializers.URLField()
    page = serializers.URLField()


class PostLikeSerializer(serializers.Serializer):
    id = serializers.URLField()
    author = AuthorSerializer()
    published = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S%z")
    object = serializers.URLField()

class PostSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=50)
    title = serializers.CharField(max_length=255)
    id = serializers.URLField()
    page = serializers.URLField()
    description = serializers.CharField(max_length=255)
    contentType = serializers.CharField(max_length=50)
    content = serializers.CharField()
    image = serializers.ImageField(required=False)
    author = AuthorSerializer()
    published = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S%z")
    visibility = serializers.CharField(max_length=50)
    likes = PostLikeSerializer(many=True)
    comments = CommentSerializer(many=True)