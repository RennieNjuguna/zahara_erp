from .models import UserPreference

def user_preferences(request):
    """
    Context processor to make user preferences available in all templates
    """
    if request.user.is_authenticated:
        try:
            prefs = request.user.preferences
        except UserPreference.DoesNotExist:
            prefs = UserPreference.objects.create(user=request.user)
        
        return {
            'user_prefs': prefs,
            # Pre-calculate simple flags for easier template logic if needed
            'is_dark_mode': prefs.theme == 'dark',
            'dashboard_currency': prefs.currency
        }
    return {'user_prefs': None}
