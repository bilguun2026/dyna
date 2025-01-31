from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.conf import settings


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
    ]
    phone = models.CharField(max_length=15, blank=True, default='')
    role = models.CharField(max_length=50, blank=True,
                            default='', choices=ROLE_CHOICES)

    def __str__(self):
        return self.username


class Table(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Column(models.Model):
    DATA_TYPES = [
        ('number', 'Number'),
        ('text', 'Text'),
        ('email', 'Email'),
        ('date', 'Date'),
        ('checkbox', 'Checkbox'),
        ('textarea', 'Textarea'),
        ('file', 'File'),
        ('image', 'Image'),
        ('select', 'Select'),
    ]
    name = models.CharField(max_length=255, db_index=True)
    table = models.ForeignKey(
        'Table', on_delete=models.CASCADE, related_name="columns", db_index=True)
    data_type = models.CharField(
        max_length=50, choices=DATA_TYPES, db_index=True)

    def __str__(self):
        return f"{self.name} ({self.data_type})"


class Option(models.Model):
    column = models.ForeignKey(
        'Column', on_delete=models.CASCADE, related_name="options")
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.value}"


class TableApi(models.Model):
    table = models.ForeignKey(
        'Table', on_delete=models.CASCADE, related_name="table_apis")
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, related_name='children', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, related_name="table_apis")


class Cell(models.Model):
    table_api = models.ForeignKey(
        'TableApi', on_delete=models.CASCADE, related_name="api_cells")
    column = models.ForeignKey(
        'Column', on_delete=models.CASCADE, related_name="column_cells")
    # Allow empty values for text-based fields
    value = models.TextField(blank=True, default='')
    file = models.FileField(upload_to='uploads/files/', blank=True, null=True)
    image = models.ImageField(
        upload_to='uploads/images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """Ensure correct validation based on column data type."""
        # Skip validation if the object is newly created (not saved in DB yet)
        if not self.pk:
            return  # Allow creation of empty cells without validation

        if self.column.data_type not in ['file', 'image'] and not self.value:
            raise ValidationError(f"Value is required for data type {
                                  self.column.data_type}.")

        if self.column.data_type == 'file' and not self.file:
            raise ValidationError("A file is required for file-type columns.")
        elif self.column.data_type == 'image' and not self.image:
            raise ValidationError(
                "An image is required for image-type columns.")

        if self.column.data_type not in ['file', 'image'] and (self.file or self.image):
            raise ValidationError(
                "Uploading files or images is not allowed for this data type.")

    def save(self, *args, **kwargs):
        self.clean()  # Run validation before saving
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cell for Column {self.column.name} in Table API {self.table_api.table.name}"
    
class Test(models.Model):
    name = models.CharField(max_length=255)
    phone = models.IntegerField()
