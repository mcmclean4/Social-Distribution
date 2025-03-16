from django import forms
from .models import Post, Author
from .models import Comment
from django.core.exceptions import ValidationError
import re

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'description', 'contentType', 'content', 'image', 'visibility']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contentType': forms.Select(attrs={'class': 'form-select'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
        }

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