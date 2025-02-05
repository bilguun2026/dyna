from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.conf import settings
import uuid


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
    ]
    phone = models.CharField(max_length=15, blank=True, default='')
    role = models.CharField(max_length=50, blank=True,
                            default='', choices=ROLE_CHOICES)

    def __str__(self):
        return self.username


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey(
        'Company', on_delete=models.CASCADE, related_name="projects"
    )


class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    project = models.ForeignKey(
        'Project', on_delete=models.CASCADE, related_name="jobs"
    )
    advisorCompanies = models.ManyToManyField(
        'Company', related_name="advised_jobs"
    )
    contractorCompanies = models.ManyToManyField(
        'Company', related_name="contracted_jobs"
    )


class Table(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Column(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
        'Table', on_delete=models.CASCADE, related_name="columns"
    )
    data_type = models.CharField(
        max_length=50, choices=DATA_TYPES, db_index=True
    )

    def __str__(self):
        return f"{self.name} ({self.data_type})"


class Option(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    column = models.ForeignKey(
        'Column', on_delete=models.CASCADE, related_name="options"
    )
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.value}"


class TableApi(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        'Job', on_delete=models.CASCADE, related_name="table_apis", blank=True, null=True
    )
    table = models.ForeignKey(
        'Table', on_delete=models.CASCADE, related_name="table_apis"
    )
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, related_name='children', null=True, blank=True
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, related_name="table_apis")


class Cell(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table_api = models.ForeignKey(
        'TableApi', on_delete=models.CASCADE, related_name="api_cells"
    )
    column = models.ForeignKey(
        'Column', on_delete=models.CASCADE, related_name="column_cells"
    )
    value = models.TextField(blank=True, default='')
    file = models.FileField(upload_to='uploads/files/', blank=True, null=True)
    image = models.ImageField(
        upload_to='uploads/images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if not self.pk:
            return

        if self.column.data_type in ['file', 'image'] and not (self.file or self.image):
            raise ValidationError(f"A file or image is required for data type {
                                  self.column.data_type}.")
        if self.column.data_type not in ['file', 'image'] and (self.file or self.image):
            raise ValidationError(
                "Uploading files or images is not allowed for this data type.")
        if self.column.data_type not in ['file', 'image'] and not self.value:
            raise ValidationError(f"Value is required for data type {
                                  self.column.data_type}.")

    def save(self, *args, **kwargs):
        self.clean()  # Run validation before saving
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cell for Column {self.column.name} in Table API {self.table_api.table.name}"
