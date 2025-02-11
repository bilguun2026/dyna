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


PROJECT_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('active', 'Active'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]

# Define choice fields for job priority.
JOB_PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('normal', 'Normal'),
    ('high', 'High'),
    ('critical', 'Critical'),
]

# Define choice fields for job status.
JOB_STATUS_CHOICES = [
    ('open', 'Open'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('on_hold', 'On Hold'),
    ('cancelled', 'Cancelled'),
]


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    established_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=50,
        choices=PROJECT_STATUS_CHOICES,
        default='pending'
    )
    budget = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True)
    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        related_name="projects"
    )

    def __str__(self):
        return self.name


class JobTableCollection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)

    def __str__(self):
        return self.name


class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    priority = models.CharField(
        max_length=50,
        choices=JOB_PRIORITY_CHOICES,
        default='normal'
    )
    status = models.CharField(
        max_length=50,
        choices=JOB_STATUS_CHOICES,
        default='open'
    )
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        related_name="jobs"
    )
    advisorCompanies = models.ManyToManyField(
        'Company',
        related_name="advised_jobs"
    )
    contractorCompanies = models.ManyToManyField(
        'Company',
        related_name="contracted_jobs"
    )
    job_table_collection = models.ForeignKey(
        'JobTableCollection', on_delete=models.CASCADE, related_name="jobs", null=True, blank=True
    )

    def __str__(self):
        return self.name


class TableCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    order_number = models.IntegerField(null=True, blank=True)
    job_table_collection = models.ForeignKey(
        'JobTableCollection', on_delete=models.CASCADE, related_name="table_categories", null=True, blank=True
    )

    def __str__(self):
        return self.name


class Table(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    job_table_collection = models.ForeignKey(
        'JobTableCollection', on_delete=models.CASCADE, related_name="tables", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey(
        'TableCategory', on_delete=models.CASCADE, related_name="tables", null=True, blank=True
    )

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
                             on_delete=models.CASCADE, related_name="table_apis", blank=True, null=True)


class Cell(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table_api = models.ForeignKey(
        TableApi, on_delete=models.CASCADE, related_name="api_cells")
    column = models.ForeignKey(
        Column, on_delete=models.CASCADE, related_name="column_cells")
    is_required = models.BooleanField(default=True)
    value = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cell for Column {self.column.name} in Table API {self.table_api}"


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cell = models.ForeignKey(
        Cell, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to='uploads/files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cell = models.ForeignKey(
        Cell, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to='uploads/images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
