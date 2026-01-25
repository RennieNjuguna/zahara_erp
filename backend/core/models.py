from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserPreference(models.Model):
    THEME_CHOICES = [
        ('light', 'Light Mode'),
        ('dark', 'Dark Mode'),
        ('system', 'System Default')
    ]
    
    TYPOGRAPHY_CHOICES = [
        ('inter', 'Inter (Modern)'),
        ('roboto', 'Roboto (Classic)'),
        ('serif', 'Merriweather (Serif)')
    ]
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('sw', 'Swahili')
    ]
    
    CURRENCY_CHOICES = [
        ('KES', 'Kenyan Shilling (KES)'),
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)')
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='light')
    typography = models.CharField(max_length=20, choices=TYPOGRAPHY_CHOICES, default='inter')
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='KES')
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s preferences"

@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    if created:
        UserPreference.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_preferences(sender, instance, **kwargs):
    instance.preferences.save()

from decouple import config

class EmailConfig(models.Model):
    """
    Store SMTP/IMAP credentials for email integration.
    Linked to User so each user can have their own email setup (optional).
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_config')
    
    # SMTP Settings (Sending)
    smtp_host = models.CharField(max_length=255, default=config('EMAIL_HOST', default='smtp.gmail.com'))
    smtp_port = models.PositiveIntegerField(default=config('EMAIL_PORT', default=587, cast=int))
    smtp_user = models.CharField(max_length=255, default=config('EMAIL_USER', default=''), help_text="Email address for sending")
    smtp_password = models.CharField(max_length=255, default=config('EMAIL_PASSWORD', default=''), help_text="App Password or Email Password")
    use_tls = models.BooleanField(default=True)
    
    # IMAP Settings (Reading/Threading)
    imap_host = models.CharField(max_length=255, default=config('EMAIL_HOST', default='imap.gmail.com'))
    imap_port = models.PositiveIntegerField(default=config('EMAIL_IMAP_PORT', default=993, cast=int))
    imap_user = models.CharField(max_length=255, default=config('EMAIL_USER', default=''), help_text="Email address for reading (usually same as smtp_user)")
    imap_password = models.CharField(max_length=255, default=config('EMAIL_PASSWORD', default=''), help_text="Usually same as smtp_password")
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Email Config for {self.user.username}"

# Signal to create EmailConfig automatically? Maybe not, better to let them configure it manually.
