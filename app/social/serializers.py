from rest_framework import serializers
from .models import Post, Author, User

# class AuthorSerializer(serializers.Serializer):
#     user = User
#     type = serializers.CharField(required=True)
#     id = serializers.URLField(required=True)
#     # host = serializers.URLField(required=True)
#     displayName = serializers.CharField(required=True)
#     github = serializers.URLField()
#     profileImage = serializers.URLField()
#     page = serializers.URLField()
#     isAdmin = serializers.BooleanField()

#     def create(self, validated_data):
#         return Author.objects.create(**validated_data)

#     def edit(self, validated_data):
#         pass

class AuthorSerializer(serializers.ModelSerializer):
    github = serializers.URLField(required=False, allow_blank=True)
    profileImage = serializers.ImageField(required=False, allow_null=True)
    page = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        model = Author
        fields = '__all__'
        extra_kwargs = {
            'user': {'read_only': True},
            'id': {'read_only': True}
        }

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
    author = AuthorSerializer()
    class Meta:
        model = Post
        fields = [
            'type', 'title', 'id', 'page', 'description',
            'contentType', 'content', 'image', 'author', 'published',
            'visibility', 'likes', 'comments'
        ]
        
        read_only_fields = ['internal_id', 'id', 'author', 'published', 'likes', 'comments']

    # Explicit .update() to avoid updating the nested author field
    def update(self, instance, validated_data):
        # Ensure 'author' is not updated by popping it from the data
        validated_data.pop('author', None)
        return super().update(instance, validated_data)

class FollowRequestSerializer(serializers.Serializer):
    type = serializers.CharField()
    summary = serializers.CharField(allow_blank=True, required=False)
    actor = AuthorSerializer()
    object = AuthorSerializer()
