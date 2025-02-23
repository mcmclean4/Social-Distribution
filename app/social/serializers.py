from rest_framework import serializers
from .models import Post, Author, User
from .models import Follow

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


class PostSerializer(serializers.ModelSerializer):
    # Make the author field read-only so it doesn't require input
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Post
        fields = [
            'internal_id', 'type', 'title', 'id', 'page', 'description',
            'contentType', 'content', 'image', 'author', 'published',
            'visibility', 'likes', 'comments'
        ]
        read_only_fields = ['internal_id', 'id', 'author', 'published', 'likes', 'comments']

class FollowRequestSerializer(serializers.Serializer):
    type = serializers.CharField()
    summary = serializers.CharField(allow_blank=True, required=False)
    actor = AuthorSerializer()
    object = AuthorSerializer()
