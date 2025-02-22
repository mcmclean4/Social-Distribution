# social/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def split_url(value):
    # This is just an example: modify the URL as needed. 
    # Here, it splits the URL by "/" and returns the last part (which post would be post.id or other.id).
    return value.split('/')[-1]

@register.filter(name='convert_to_int')
def convert_to_int(value):
    try:
        return int(value)
    except ValueError:
        return value
    
@register.filter(name='get_type')
def get_type(value):
    return type(value).__name__