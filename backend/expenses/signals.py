from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from django.core.files.storage import default_storage
from .models import Expense, ExpenseAttachment


@receiver(pre_save, sender=ExpenseAttachment)
def save_original_filename(sender, instance, **kwargs):
    """Save original filename before file is processed"""
    if instance.file and not instance.original_filename:
        instance.original_filename = instance.file.name.split('/')[-1]


@receiver(post_delete, sender=ExpenseAttachment)
def delete_file_on_attachment_delete(sender, instance, **kwargs):
    """Delete file from storage when attachment is deleted"""
    if instance.file:
        try:
            default_storage.delete(instance.file.name)
        except Exception:
            # File might already be deleted or not accessible
            pass


@receiver(post_delete, sender=Expense)
def delete_attachments_on_expense_delete(sender, instance, **kwargs):
    """Delete all attachments when expense is deleted"""
    for attachment in instance.attachments.all():
        attachment.delete()
