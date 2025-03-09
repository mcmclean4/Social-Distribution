from rest_framework import serializers
from .models import Post, Author, User, Comment, Like

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
    profileImage = serializers.ImageField(required=False, allow_null=True)
    page = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        model = Author
        # fields = '__all__'
        fields = ['type', 'id', 'host' , 'displayName', 'github', 'profileImage', 'page']
        extra_kwargs = {
            'user': {'read_only': True},
            'id': {'read_only': True}
        }

class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['type', 'id', 'author', 'comment', 'contentType', 'published', 'post']
        read_only_fields = ['id', 'published', 'type']
        
    def to_representation(self, instance):
        # Custom representation to match the required API format
        representation = super().to_representation(instance)
        # Add any additional formatting if needed
        return representation

class LikeSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    
    class Meta:
        model = Like
        fields = ['type', 'id', 'author', 'object', 'published']
        read_only_fields = ['id', 'published', 'type']


class PostSerializer(serializers.ModelSerializer):
    # Make the author field read-only so it doesn't require input
    author = AuthorSerializer()
    comments = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()
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
    
    def get_comments(self, obj):
        # Get all comments for this post
        comments = Comment.objects.filter(post=obj.id)
        
        # Serialize the comments
        comment_serializer = CommentSerializer(comments, many=True)
        
        # Return the comments in the required format
        return {
            "type": "comments",
            "id": f"{obj.id}/comments",
            "page": f"{obj.page}/comments" if obj.page else None,
            "page_number": 1,
            "size": 5,
            "count": comments.count(),
            "src": comment_serializer.data,
        }
    
    def get_likes(self, obj):
        # Get all likes for this post
        likes = Like.objects.filter(object=obj.id)
        
        # Debug by printing the query and results
        print(f"Post ID: {obj.id}")
        print(f"Looking for likes where object={obj.id}")
        print(f"Found likes: {likes.count()}")
        
        # You can also print all likes to see what their object values are
        all_likes = Like.objects.all()
        print(f"All likes in the system:")
        for like in all_likes:
            print(f"Like ID: {like.id}, Object: {like.object}")
        
        # Serialize the likes
        like_serializer = LikeSerializer(likes, many=True)
        
        # Return the likes in the required format
        return {
            "type": "likes",
            "id": f"{obj.id}/likes",
            "page": f"{obj.page}/likes" if obj.page else None,
            "page_number": 1,
            "size": 50,
            "count": likes.count(),
            "src": like_serializer.data,
        }
class FollowRequestSerializer(serializers.Serializer):
    type = serializers.CharField()
    summary = serializers.CharField(allow_blank=True, required=False)
    actor = AuthorSerializer()
    object = AuthorSerializer()
