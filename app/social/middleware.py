import re
import io
from django.http import HttpResponse, HttpResponseForbidden
import base64

class SecurityMiddleware:
    """
    Middleware to provide additional security against malicious requests.
    """
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024
    
    # Content types that are explicitly allowed
    ALLOWED_CONTENT_TYPES = [
        'text/plain',
        'text/markdown',
        'text/html',
        'application/base64',
        'image/png;base64',
        'image/jpeg;base64',
        'video/mp4;base64',
        'video/webm;base64',
        'multipart/form-data',
    ]
    
    # Common video signature bytes
    VIDEO_SIGNATURES = {
        'mp4': [b'\x00\x00\x00\x18\x66\x74\x79\x70', b'\x00\x00\x00\x20\x66\x74\x79\x70'],
        'webm': [b'\x1A\x45\xDF\xA3']
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.method == 'POST':
            # Size check
            content_length = request.META.get('CONTENT_LENGTH')
            if content_length is not None:
                try:
                    if int(content_length) > self.MAX_UPLOAD_SIZE:
                        return HttpResponse("Request body too large (limit is 50 MB)", status=413)
                except ValueError:
                    return HttpResponseForbidden("Invalid Content-Length header")
            
            # Content-type check for the overall request
            content_type = request.META.get('CONTENT_TYPE', '').split(';')[0]
            
            # Check if multipart form data (file uploads) or one of our allowed content types
            is_allowed_content = False
            for allowed_type in self.ALLOWED_CONTENT_TYPES:
                base_allowed_type = allowed_type.split(';')[0]
                if content_type.startswith(base_allowed_type) or content_type == 'multipart/form-data':
                    is_allowed_content = True
                    break
            
            # If not allowed content type, check for malicious patterns
            if not is_allowed_content:
                all_patterns = self._get_security_patterns()
                
                # Check POST data
                for key, value in request.POST.items():
                    if isinstance(value, str):
                        for pattern in all_patterns:
                            if re.search(pattern, value, re.IGNORECASE):
                                return HttpResponseForbidden("Malicious content detected")
            
            # Special handling for file uploads - always check these
            for key, file in request.FILES.items():
                # Check filename for malicious content
                if hasattr(file, 'name'):
                    filename = file.name.lower()
                    
                    # Whitelist file extensions for safety
                    allowed_extensions = {
                        'image': ['.jpg', '.jpeg', '.png', '.gif','.webp'],
                        'video': ['.mp4', '.webm']
                    }
                    
                    # Check if this is a video file specifically
                    if key == 'video':  
                        valid_ext = False
                        for ext in allowed_extensions['video']:
                            if filename.endswith(ext):
                                valid_ext = True
                                break
                                
                        if not valid_ext:
                            return HttpResponseForbidden(f"Invalid video file extension. Allowed: {', '.join(allowed_extensions['video'])}")
                            
                        # Basic content check for videos - first 16 bytes should be enough
                        if hasattr(file, 'read') and hasattr(file, 'seek'):
                            file_header = file.read(16)
                            file.seek(0)  # Reset file pointer
                            
                            valid_video = False
                            for format_type, signatures in self.VIDEO_SIGNATURES.items():
                                for sig in signatures:
                                    # Check if signature is in the header (not necessarily at the start)
                                    if sig in file_header:
                                        valid_video = True
                                        break
                                        
                            valid_video = True
                            
                            if not valid_video:
                                return HttpResponseForbidden("Invalid video format or corrupted file")
                    
                    # Specialized handling for base64 content
                    if key == 'content' and 'base64' in request.POST.get('contentType', ''):
                        try:
                            # Try to decode a small sample to validate 
                            content_sample = request.POST.get('content', '')[:1000]
                            if ';base64,' in content_sample:
                                content_sample = content_sample.split(';base64,')[1]
                            base64.b64decode(content_sample)
                        except:
                            return HttpResponseForbidden("Invalid base64 content")
        
        return self.get_response(request)
    
    def _get_security_patterns(self):
        sql_injection_patterns = [
            r'(\%27)|(\')|(\-\-)|(\%23)|(#)',
            r'((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))',
            r'/\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))',
            r'((\%27)|(\'))union',
            r'exec(\s|\+)+(s|x)p\w+',
        ]
        
        xss_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'onerror=',
            r'onload=',
            r'eval\(',
            r'document\.cookie',
            r'document\.write',
            r'<iframe.*?>.*?</iframe>',
        ]
        
        command_injection_patterns = [
            r'[;&|`]',
            r'\$\(.*?\)',
            r'\$\{.*?\}',
            r'`.*?`',
            r'\|.*?\|',
            r'&&.*?&&',
            r';.*?;',
        ]
        
        return sql_injection_patterns + xss_patterns + command_injection_patterns