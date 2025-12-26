from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class ExpenseCategory(models.Model):
    """Categories for organizing expenses (e.g., Office Supplies, Travel, Marketing)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=7, default="#007bff", help_text="Hex color code for UI display")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Expense Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    """Main expense record with all details"""

    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('KSH', 'Kenya Shilling'),
        ('GBP', 'British Pound'),
    ]

    # Basic Information
    name = models.CharField(max_length=200, help_text="Name or description of the expense")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Amount of the expense"
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='KSH')
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Invoice number, receipt number, or other reference"
    )

    # Categorization
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )

    # Details
    description = models.TextField(blank=True, null=True, help_text="Detailed description of the expense")
    date_incurred = models.DateField(default=timezone.now, help_text="Date when the expense was incurred")
    due_date = models.DateField(blank=True, null=True, help_text="Due date for payment if applicable")

    # Status and Approval
    description = models.TextField(blank=True, null=True, help_text="Detailed description of the expense")
    date_incurred = models.DateField(default=timezone.now, help_text="Date when the expense was incurred")
    due_date = models.DateField(blank=True, null=True, help_text="Due date for payment if applicable")

    # Payment Information
    payment_method = models.CharField(max_length=100, blank=True, null=True, help_text="How the expense was paid")
    payment_date = models.DateField(blank=True, null=True, help_text="Date when payment was made")

    # Vendor/Supplier Information
    vendor_name = models.CharField(max_length=200, blank=True, null=True, help_text="Name of vendor or supplier")
    vendor_contact = models.CharField(max_length=200, blank=True, null=True, help_text="Contact information for vendor")

    # Additional Fields
    is_recurring = models.BooleanField(default=False, help_text="Is this a recurring expense?")
    recurring_frequency = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
            ('weekly', 'Weekly'),
        ],
        help_text="Frequency if this is a recurring expense"
    )
    tags = models.CharField(max_length=500, blank=True, null=True, help_text="Comma-separated tags for easy searching")

    # Metadata
    created_by = models.CharField(max_length=100, blank=True, null=True, help_text="Person who created this expense record")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_incurred', '-created_at']
        indexes = [
            models.Index(fields=['date_incurred']),
            models.Index(fields=['category']),
            models.Index(fields=['currency']),
        ]

    def __str__(self):
        return f"{self.name} - {self.amount} {self.currency}"

    def get_total_with_currency(self):
        """Return formatted amount with currency"""
        return f"{self.amount} {self.currency}"

    def is_overdue(self):
        """Check if expense payment is overdue"""
        if self.due_date and not self.payment_date:
            return timezone.now().date() > self.due_date
        return False

    def get_days_overdue(self):
        """Get number of days overdue"""
        if self.is_overdue():
            return (timezone.now().date() - self.due_date).days
        return 0


class ExpenseAttachment(models.Model):
    """Files attached to expenses (receipts, invoices, etc.)"""

    ATTACHMENT_TYPES = [
        ('receipt', 'Receipt'),
        ('invoice', 'Invoice'),
        ('photo', 'Photo'),
        ('document', 'Document'),
        ('other', 'Other'),
    ]

    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='expense_attachments/%Y/%m/%d/', help_text="Upload receipt, invoice, or other document")
    file_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPES, default='receipt')
    original_filename = models.CharField(max_length=255, help_text="Original filename before upload")
    description = models.CharField(max_length=200, blank=True, null=True, help_text="Description of the attachment")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.expense.name} - {self.get_file_type_display()}"

    def get_file_extension(self):
        """Get file extension from original filename"""
        if self.original_filename:
            return self.original_filename.split('.')[-1].lower()
        return ''

    def is_image(self):
        """Check if attachment is an image"""
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        return self.get_file_extension() in image_extensions

    def is_pdf(self):
        """Check if attachment is a PDF"""
        return self.get_file_extension() == 'pdf'
