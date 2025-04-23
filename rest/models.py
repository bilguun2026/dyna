from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.conf import settings
import uuid
from django.db.models import F
from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver
from celery import shared_task
import threading


thread_local = threading.local()


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


# Project Status Choices
PROJECT_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('active', 'Active'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]

# Job Priority Choices
JOB_PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('normal', 'Normal'),
    ('high', 'High'),
    ('critical', 'Critical'),
]

# Job Status Choices
JOB_STATUS_CHOICES = [
    ('open', 'Open'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('on_hold', 'On Hold'),
    ('cancelled', 'Cancelled'),
]

# Company Model


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

# Project Model


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

# JobTableCollection Model


class JobTableCollection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)

    def __str__(self):
        return self.name

# Job Model


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

# TableCategory Model


class TableCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    order_number = models.IntegerField(null=True, blank=True)
    job_table_collection = models.ForeignKey(
        'JobTableCollection', on_delete=models.CASCADE, related_name="table_categories", null=True, blank=True
    )

    def __str__(self):
        return self.name

# Table Model


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

# Operation Model


class Operation(models.Model):
    name = models.CharField(max_length=50, unique=True, choices=[
        ('add', 'Addition (+)'),
        ('subtract', 'Subtraction (-)'),
        ('multiply', 'Multiplication (*)'),
        ('divide', 'Division (/)'),
        ('sqrt', 'Square Root (sqrt)'),
        ('percent', 'Percentage (%)'),
    ])
    # Increased length for 'sqrt' and 'percent'
    symbol = models.CharField(max_length=10)

    def __str__(self):
        return self.name

    def apply(self, operand):
        """Apply the operation to the operand."""
        if self.name == 'add':
            return lambda x, y: x + y
        elif self.name == 'subtract':
            return lambda x, y: x - y
        elif self.name == 'multiply':
            return lambda x, y: x * y
        elif self.name == 'divide':
            return lambda x, y: x / y if y != 0 else float('nan')
        elif self.name == 'sqrt':
            return lambda x: x ** 0.5 if x >= 0 else float('nan')
        elif self.name == 'percent':
            return lambda x: x * 0.01

# FormulaOperand Model


class FormulaOperand(models.Model):
    column = models.ForeignKey(
        'Column', on_delete=models.CASCADE, null=True, blank=True,
        help_text="The column operand (if applicable)."
    )
    constant = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="The constant operand (if applicable)."
    )

    def __str__(self):
        if self.column:
            return f"Column: {self.column.name}"
        elif self.constant is not None:
            return f"Constant: {self.constant}"
        return "No Operand"

# FormulaStep Model


class FormulaStep(models.Model):
    column = models.ForeignKey(
        'Column', on_delete=models.CASCADE, related_name="steps",
        help_text="The column this step belongs to."
    )
    operation = models.ForeignKey(
        Operation, on_delete=models.CASCADE, null=True, blank=True,
        help_text="The operation to apply (e.g., +, -, *, /, sqrt, %)."
    )
    operand = models.ForeignKey(
        FormulaOperand, on_delete=models.CASCADE, null=True, blank=True,
        help_text="The operand for this step (column or constant)."
    )
    order = models.IntegerField(
        default=0, help_text="Order of this step in the formula."
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        if self.operand and self.operand.column:
            return f"{self.column.name} -> {self.operand.column.name} {self.operation.symbol if self.operation else ''}"
        elif self.operand and self.operand.constant is not None:
            return f"{self.column.name} -> {self.operand.constant} {self.operation.symbol if self.operation else ''}"
        return f"{self.column.name} (No Operand)"

# Column Model


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
    formula_text = models.TextField(
        blank=True,
        help_text="Enter the formula as a string (e.g., 'sqrt(W_1) + W_2 % * (W_3 - W_1)'). Supported operations: +, -, *, /, sqrt(), %"
    )

    def __str__(self):
        return f"{self.name} ({self.data_type})"

# Option Model


class Option(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    column = models.ForeignKey(
        'Column', on_delete=models.CASCADE, related_name="options"
    )
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.value}"

# TableApi Model


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


# Cell Model


class Cell(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table_api = models.ForeignKey(
        TableApi, on_delete=models.CASCADE, related_name="api_cells")
    column = models.ForeignKey(
        Column, on_delete=models.CASCADE, related_name="column_cells")
    is_required = models.BooleanField(default=True)
    value = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['table_api', 'column']),
        ]

    def __str__(self):
        return f"Cell for Column {self.column.name} in Table API {self.table_api}"

    @property
    def computed_value(self):
        cache_key = f"cell_computed_value_{self.id}"
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cached_value

        formula_steps = FormulaStep.objects.filter(
            column=self.column).order_by('order')
        if not formula_steps.exists() or self.column.data_type != 'number':
            return self.value

        try:
            sibling_cells = self.table_api.api_cells.select_related('column')
            result = None

            for step in formula_steps:
                if step.operand and step.operand.column:
                    ref_cell = sibling_cells.filter(
                        column=step.operand.column).first()
                    if not ref_cell:
                        ref_cell = Cell.objects.create(
                            table_api=self.table_api,
                            column=step.operand.column,
                            value=""
                        )
                    operand = float(ref_cell.computed_value or 0)
                elif step.operand and step.operand.constant is not None:
                    operand = float(step.operand.constant)
                elif result is not None:
                    operand = result
                else:
                    operand = 0

                if result is None:
                    result = operand
                elif step.operation:
                    operation_func = step.operation.apply(operand)
                    if step.operation.name in ['sqrt', 'percent']:
                        result = operation_func(result)
                    else:
                        # For binary operations, get the next operand
                        next_step = next(
                            (s for s in formula_steps if s.order > step.order), None)
                        if next_step and next_step.operand and next_step.operand.column:
                            next_ref_cell = sibling_cells.filter(
                                column=next_step.operand.column).first()
                            if not next_ref_cell:
                                next_ref_cell = Cell.objects.create(
                                    table_api=self.table_api,
                                    column=next_step.operand.column,
                                    value=""
                                )
                            next_operand = float(
                                next_ref_cell.computed_value or 0)
                            result = operation_func(result, next_operand)
                        elif next_step and next_step.operand and next_step.operand.constant is not None:
                            next_operand = float(next_step.operand.constant)
                            result = operation_func(result, next_operand)
                        else:
                            raise ValueError(
                                f"No operand for operation {step.operation.name}")
                # Debug output
                print(f"Step {step.order}: operand={operand}, result={result}")

            cache.set(cache_key, str(result), timeout=3600)  # Cache for 1 hour
            return str(result) if result is not None else self.value
        except Exception as e:
            return f"Error in formula: {str(e)}"

    def save(self, *args, **kwargs):
        if FormulaStep.objects.filter(column=self.column).exists():
            self.value = self.computed_value
        super().save(*args, **kwargs)

# File Model


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cell = models.ForeignKey(
        Cell, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to='uploads/files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

# Image Model


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cell = models.ForeignKey(
        Cell, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to='uploads/images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

# Celery Task for Dependency Updates


@shared_task
def update_dependent_cells_task(cell_id):
    try:
        # Set the thread-local flag to indicate this is a task-driven update
        thread_local.update_from_task = True
        try:
            cell = Cell.objects.get(id=cell_id)
            print(f"Processing cell {cell_id} with column {cell.column.name}")
            # Find FormulaStep instances where this column is an operand
            dependent_steps = FormulaStep.objects.filter(
                operand__column=cell.column
                # Exclude the current column to avoid self-reference
            ).exclude(column=cell.column)
            print(f"Found dependent steps: {list(dependent_steps)}")
            # Find columns that have these dependent steps
            dependent_columns = Column.objects.filter(
                steps__in=dependent_steps
            ).distinct()
            print(f"Found dependent columns: {list(dependent_columns)}")

            # Update the current cell if it has a formula
            if FormulaStep.objects.filter(column=cell.column).exists():
                print(
                    f"Updating current cell {cell.column.name} with computed value {cell.computed_value}")
                cell.value = cell.computed_value
                cell.save(update_fields=['value'])

            # Update dependent cells in the same TableApi
            for dep_column in dependent_columns:
                dependent_cells = cell.table_api.api_cells.filter(
                    column=dep_column)
                for dep_cell in dependent_cells:
                    print(
                        f"Updating cell for column {dep_cell.column.name} with value {dep_cell.computed_value}")
                    dep_cell.value = dep_cell.computed_value
                    dep_cell.save(update_fields=['value'])
        finally:
            # Reset the thread-local flag
            thread_local.update_from_task = False
    except Cell.DoesNotExist:
        print(f"Cell with id {cell_id} not found")

# Signal to Trigger Dependency Updates


@receiver(post_save, sender=Cell)
def trigger_update_dependent_cells(sender, instance, **kwargs):
    # Avoid triggering on task updates
    if not getattr(thread_local, 'update_from_task', False):
        update_dependent_cells_task.delay(instance.id)
