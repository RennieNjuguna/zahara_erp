from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserPreference, EmailConfig

@login_required
def settings_view(request):
    try:
        user_pref = request.user.preferences
    except UserPreference.DoesNotExist:
        user_pref = UserPreference.objects.create(user=request.user)

    try:
        email_config = request.user.email_config
    except EmailConfig.DoesNotExist:
        email_config = EmailConfig.objects.create(user=request.user)

    if request.method == 'POST':
        try:
            # Save Preferences
            user_pref.theme = request.POST.get('theme', 'light')
            user_pref.typography = request.POST.get('typography', 'inter')
            user_pref.language = request.POST.get('language', 'en')
            user_pref.currency = request.POST.get('currency', 'KES')
            user_pref.save()

            # Save Email Config
            email_config.smtp_host = request.POST.get('smtp_host')
            email_config.smtp_port = int(request.POST.get('smtp_port', 587))
            email_config.smtp_user = request.POST.get('smtp_user')
            
            # Only update password if provided (don't clear it on empty submit)
            smtp_pass = request.POST.get('smtp_password')
            if smtp_pass:
                email_config.smtp_password = smtp_pass
                
            email_config.use_tls = request.POST.get('use_tls') == 'on'
            
            email_config.imap_host = request.POST.get('imap_host')
            email_config.imap_port = int(request.POST.get('imap_port', 993))
            email_config.imap_user = request.POST.get('imap_user')
            
            imap_pass = request.POST.get('imap_password')
            if imap_pass:
                email_config.imap_password = imap_pass
                
            email_config.save()

            messages.success(request, 'Settings updated successfully!')
            return redirect('core:settings')
        except Exception as e:
            messages.error(request, f'Error saving settings: {str(e)}')

    context = {
        'preferences': user_pref,
        'email_config': email_config,
        'THEME_CHOICES': UserPreference.THEME_CHOICES,
        'TYPOGRAPHY_CHOICES': UserPreference.TYPOGRAPHY_CHOICES,
        'LANGUAGE_CHOICES': UserPreference.LANGUAGE_CHOICES,
        'CURRENCY_CHOICES': UserPreference.CURRENCY_CHOICES,
    }
    return render(request, 'core/settings.html', context)
