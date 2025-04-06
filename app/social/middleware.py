import re
from django.http import HttpResponse, HttpResponseForbidden

class SecurityMiddleware:
    """
    Middleware to provide additional security against malicious requests.
    """
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST':
            content_length = request.META.get('CONTENT_LENGTH')
            if content_length is not None:
                try:
                    if int(content_length) > self.MAX_UPLOAD_SIZE:
                        return HttpResponse("Request body too large (limit is 50 MB)", status=413)
                except ValueError:
                    return HttpResponseForbidden("Invalid Content-Length header")

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
                r'<img.*?src=.*?>',
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

            all_patterns = sql_injection_patterns + xss_patterns + command_injection_patterns

            for key, value in request.POST.items():
                if isinstance(value, str):
                    for pattern in all_patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            return HttpResponseForbidden("Malicious content detected")

            for key, file in request.FILES.items():
                if hasattr(file, 'name'):
                    for pattern in all_patterns:
                        if re.search(pattern, file.name, re.IGNORECASE):
                            return HttpResponseForbidden("Malicious filename detected")

        return self.get_response(request)
