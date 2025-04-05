import re
from django.http import HttpResponseForbidden
from django.conf import settings

class SecurityMiddleware:
    """
    Middleware to provide additional security against malicious requests.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Check for malicious content in POST data
        if request.method == 'POST':
            # Check for potential SQL injection patterns
            sql_injection_patterns = [
                r'(\%27)|(\')|(\-\-)|(\%23)|(#)',
                r'((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))',
                r'/\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))',
                r'((\%27)|(\'))union',
                r'exec(\s|\+)+(s|x)p\w+',
            ]
            
            # Check for potential XSS patterns
            xss_patterns = [
                r'<script.*?>.*?</script>',
                r'javascript:',
                r'onerror=',
                r'onload=',
                r'eval\(',
                r'document\.cookie',
                r'document\.write',
                r'<img.*?src=.*?>',
                r'<iframe.*?>.*?</iframe>',
            ]
            
            # Check for potential command injection patterns
            command_injection_patterns = [
                r'[;&|`]',
                r'\$\(.*?\)',
                r'\$\{.*?\}',
                r'`.*?`',
                r'\|.*?\|',
                r'&&.*?&&',
                r';.*?;',
            ]
            
            # Combine all patterns
            all_patterns = sql_injection_patterns + xss_patterns + command_injection_patterns
            
            # Check POST data
            for key, value in request.POST.items():
                if isinstance(value, str):
                    for pattern in all_patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            return HttpResponseForbidden("Malicious content detected")
            
            # Check FILES data
            for key, file in request.FILES.items():
                if hasattr(file, 'name'):
                    for pattern in all_patterns:
                        if re.search(pattern, file.name, re.IGNORECASE):
                            return HttpResponseForbidden("Malicious filename detected")
        
        # Process the request normally
        response = self.get_response(request)
        return response 