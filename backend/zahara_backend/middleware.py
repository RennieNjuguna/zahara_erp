from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

class LoginRequiredMiddleware:
    """
    Middleware that requires a user to be authenticated to view any page.
    Exempts the login page, static files, and API endpoints.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            # Exemptions
            path = request.path_info
            
            # Allow access to login page
            if path == settings.LOGIN_URL:
                return self.get_response(request)
            
            # Allow access to static and media files
            if path.startswith(settings.STATIC_URL) or path.startswith(settings.MEDIA_URL):
                return self.get_response(request)
                
            # Allow access to admin site (it handles its own login)
            if path.startswith('/admin/'):
                return self.get_response(request)
                
            # Allow access to API (it handles its own auth)
            if path.startswith('/api/'):
                return self.get_response(request)
            
            # Redirect to login page for everything else
            return redirect(f'{settings.LOGIN_URL}?next={request.path}')

        response = self.get_response(request)
        return response
