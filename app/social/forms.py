from django import forms
from .models import Post, Author
from .models import Comment
from django.core.exceptions import ValidationError
import re
import html
import bleach
import base64
from PIL import Image
from io import BytesIO

class PostForm(forms.ModelForm):
    image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}), help_text="Upload a image (max 10MB)")
    video = forms.FileField(required=False, help_text="Upload a video (MP4, WebM, max 50MB)")
    class Meta:
        model = Post
        fields = ['title', 'description', 'contentType', 'content', 'visibility']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'contentType': forms.Select(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'visibility': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude 'DELETED' from the visibility choices
        self.fields['visibility'].choices = [
            choice for choice in Post.CONTENT_VISIBILITY_CHOICES if choice[0] != 'DELETED']
        # Make content field not required at the form level
        self.fields['content'].required = False

    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('contentType', '')
        content = cleaned_data.get('content', '')
        title = cleaned_data.get('title', '')
        description = cleaned_data.get('description', '')

        VALID_CONTENT_TYPES = [
            'text/plain', 'text/markdown', 'text/html',
            'application/base64', 'image/png;base64', 'image/jpeg;base64',
            'video/mp4;base64', 'video/webm;base64']
        
        # Ensure valid contentType
        if content_type not in VALID_CONTENT_TYPES:
            self.add_error('contentType', 'Invalid content type.')

        # Validate title
        if title:
            if len(title) > 100:
                self.add_error('title', 'Title must be less than 100 characters.')
            if not re.match(r'^[a-zA-Z0-9\s.,!?()-]+$', title):
                self.add_error('title', 'Title contains invalid characters.')
            cleaned_data['title'] = html.escape(title)

        # Validate description
        if description:
            if len(description) > 500:
                self.add_error('description', 'Description must be less than 500 characters.')
            if not re.match(r'^[a-zA-Z0-9\s.,!?()-]+$', description):
                self.add_error('description', 'Description contains invalid characters.')
            cleaned_data['description'] = html.escape(description)

        # Validate content based on content type
        if content:
            if len(content.encode('utf-8')) > 10 * 1024 * 1024:  # max 10MB
                self.add_error('content', 'Content exceeds 10MB.')

            if content_type == 'text/plain':
                if not re.match(r'^[\w\s.,!?()\-\n]+$', content):
                    self.add_error('content', 'Text content contains invalid characters.')
                cleaned_data['content'] = html.escape(content)

            elif content_type == 'text/markdown':
                cleaned_data['content'] = bleach.clean(content, strip=True)

            elif content_type == 'text/html':
                cleaned_data['content'] = bleach.clean(
                    content,
                    tags=['p', 'br', 'b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li'],
                    attributes={'a': ['href']},
                    strip=True
                )

            # elif content_type in ['image/png;base64', 'image/jpeg;base64', 'application/base64']:
            #     try:
            #         header, b64data = content.split(',', 1) if ',' in content else (None, content)
            #         binary_data = base64.b64decode(b64data)
            #         if len(binary_data) > 10 * 1024 * 1024:
            #             self.add_error('content', 'Base64 image exceeds 10MB.')
            #         img = Image.open(BytesIO(binary_data))
            #         img.verify()

            #         if content_type == 'image/png;base64' and img.format != 'PNG':
            #             self.add_error('content', 'Expected PNG image.')
            #         elif content_type == 'image/jpeg;base64' and img.format != 'JPEG':
            #             self.add_error('content', 'Expected JPEG image.')
            #         elif content_type == 'application/base64' and img.format in ['PNG', 'JPEG', 'GIF']:
            #             self.add_error('content', 'Use correct image content type for PNG/JPEG.')
            #     except Exception:
            #         self.add_error('content', 'Invalid base64 image.')

        # Validate file uploads
        image = self.files.get('image')
        if image:
            if image.size > 10 * 1024 * 1024:
                self.add_error('image', 'Image file size must be less than 10MB.')

        video = self.files.get('video')
        if video:
            if video.size > 50 * 1024 * 1024:
                self.add_error('video', 'Video file size must be less than 50MB.')

        return cleaned_data

class EditProfileForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ['displayName', 'profileImage']
        
    def clean_profileImage(self):
        profile_image_url = self.cleaned_data.get('profileImage')
        
        # Check if the URL ends with .jpeg or .png
        if profile_image_url:
            if not re.match(r'^https?://.*\.(jpeg|jpg|png)$', profile_image_url, re.IGNORECASE):
                raise forms.ValidationError("Please provide a valid image URL (ending in .jpeg, .jpg, or .png).")
        
        return profile_image_url
    
    def clean_displayName(self):
        display_name = self.cleaned_data['displayName']
        # Check if displayName is already taken
        if Author.objects.filter(displayName=display_name).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("This display name is already taken. Please choose another one.")
        return display_name

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['comment', 'contentType']

        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'contentType': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('contentType', '')
        content = cleaned_data.get('content', '')

        if content_type == 'text/plain':
            if len(content) > 10000:
                self.add_error('content', 'Text content is too long.')
            if not re.match(r'^[\w\s.,!?()-\n]+$', content):
                self.add_error('content', 'Text content contains invalid characters.')
            cleaned_data['content'] = html.escape(content)

        elif content_type == 'text/markdown':
            if len(content) > 10000:
                self.add_error('content', 'Text content is too long.')
            cleaned_data['content'] = bleach.clean(content, strip=True)
            
        elif content_type == 'text/html':
            if len(content) > 10000:
                self.add_error('content', 'HTML content is too long.')
            cleaned_data['content'] = bleach.clean(
                content,
                tags=['p', 'br', 'b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li'],
                attributes={'a': ['href']},
                strip=True
            )

        return cleaned_data
    
class RegisterForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    displayName = forms.CharField(max_length=100)
    github = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise ValidationError("The two password fields must match.")
        return cleaned_data