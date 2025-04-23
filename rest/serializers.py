from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import (
    File, FormulaOperand, Image, JobTableCollection, TableCategory, User, Company, Project, Job,
    Table, Column, Option, TableApi, Cell, Operation, FormulaStep
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.exceptions import ValidationError
import logging
# ----- OPERATION SERIALIZER -----


class OperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Operation
        fields = ['id', 'name', 'symbol']

# ----- FORMULA STEP SERIALIZER -----


class FormulaOperandSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormulaOperand
        fields = ['id', 'column', 'constant']


class FormulaStepSerializer(serializers.ModelSerializer):
    column = serializers.PrimaryKeyRelatedField(
        queryset=Column.objects.all(), required=False
    )
    operation = serializers.PrimaryKeyRelatedField(
        queryset=Operation.objects.all(), required=False, allow_null=True
    )
    operand = FormulaOperandSerializer(required=False, allow_null=True)

    class Meta:
        model = FormulaStep
        fields = ['id', 'column', 'operation', 'operand', 'order']

    def validate(self, data):
        # Ensure an operand is provided if an operation is specified
        if data.get('operation') and not data.get('operand'):
            raise serializers.ValidationError(
                "An operand must be provided if an operation is specified."
            )
        # Ensure column is provided
        if not data.get('column'):
            raise serializers.ValidationError("A column must be provided.")
        return data

    def create(self, validated_data):
        operand_data = validated_data.pop('operand', None)
        if operand_data:
            operand = FormulaOperand.objects.create(**operand_data)
            validated_data['operand'] = operand
        return FormulaStep.objects.create(**validated_data)

    def update(self, instance, validated_data):
        operand_data = validated_data.pop('operand', None)
        if operand_data:
            if instance.operand:
                # Update existing operand
                for key, value in operand_data.items():
                    setattr(instance.operand, key, value)
                instance.operand.save()
            else:
                # Create new operand
                instance.operand = FormulaOperand.objects.create(
                    **operand_data)
        elif operand_data == {}:  # Explicitly set operand to null
            instance.operand = None
        return super().update(instance, validated_data)

# ----- USER SERIALIZER -----


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        validated_data['password'] = make_password(
            validated_data.get('password'))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(
                validated_data.get('password'))
        return super().update(instance, validated_data)

# ----- COMPANY SERIALIZER -----


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"

# ----- OPTION SERIALIZER -----


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'value']

# ----- COLUMN SERIALIZER -----


class ColumnSerializer(serializers.ModelSerializer):
    # Only include options if the column is of type 'select'
    options = serializers.SerializerMethodField()
    # Include formula steps for columns with formulas
    formula_steps = FormulaStepSerializer(many=True, read_only=True)

    class Meta:
        model = Column
        fields = ['id', 'name', 'data_type', 'options', 'formula_steps']

    def get_options(self, obj):
        if obj.data_type == 'select':
            options = obj.options.all()
            return OptionSerializer(options, many=True).data
        return None

# ----- TABLE SERIALIZER -----


class TableSerializer(serializers.ModelSerializer):
    # Use the nested ColumnSerializer to show related columns
    columns = ColumnSerializer(many=True, read_only=True)

    class Meta:
        model = Table
        fields = ['id', 'name', 'created_at', 'columns']

# ----- FILE SERIALIZER -----


class FileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ['cell', 'file']


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ['id', 'cell', 'file', 'uploaded_at']

# ----- IMAGE SERIALIZER -----


class ImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ['cell', 'image']


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ['id', 'cell', 'image', 'uploaded_at']

# ----- CELL SERIALIZER -----


class CellSerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    # Add computed_value to expose the formula result
    computed_value = serializers.ReadOnlyField()

    class Meta:
        model = Cell
        fields = ['id', 'column', 'value', 'computed_value',
                  'files', 'images', 'created_at']

# ----- TABLE API SERIALIZER -----


class TableApiSerializer(serializers.ModelSerializer):
    api_cells = CellSerializer(many=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = TableApi
        fields = ['id', 'table', 'user', 'api_cells', 'children']

    def get_children(self, obj):
        # Recursively serialize child TableApis
        children = obj.children.all()
        return TableApiSerializer(children, many=True).data

    def validate_api_cells(self, cells_data):
        if not cells_data:
            return cells_data

        # Group cells by implied row (assuming order defines rows)
        table = self.initial_data.get('table')
        if not table:
            raise serializers.ValidationError(
                "Table is required to validate columns.")
        table_obj = Table.objects.get(id=table)
        column_names = table_obj.columns.values_list('name', flat=True)

        row_cells = []
        current_row = []
        for cell_data in cells_data:
            column_id = cell_data.get('column')
            column = Column.objects.get(id=column_id)
            if column.name not in column_names:
                raise serializers.ValidationError(
                    f"Column {column.name} not in table.")
            current_row.append(cell_data)
            # Assume a new row starts when all columns are covered
            if len(current_row) == table_obj.columns.count():
                row_cells.append(current_row)
                current_row = []
        if current_row:
            row_cells.append(current_row)

        return cells_data  # Return original data after validation

    def create(self, validated_data):
        api_cells_data = validated_data.pop('api_cells', [])
        table_api = TableApi.objects.create(**validated_data)
        cell_instances = [Cell(table_api=table_api, **cell_data)
                          for cell_data in api_cells_data]
        Cell.objects.bulk_create(cell_instances)
        return table_api

    def update(self, instance, validated_data):
        api_cells_data = validated_data.pop('api_cells', [])
        instance.table = validated_data.get('table', instance.table)
        instance.user = validated_data.get('user', instance.user)
        instance.save()

        # Remove cells that are not in the incoming data
        existing_ids = set(instance.api_cells.values_list('id', flat=True))
        incoming_ids = {cell_data.get(
            'id') for cell_data in api_cells_data if 'id' in cell_data}
        to_delete_ids = existing_ids - incoming_ids
        Cell.objects.filter(id__in=to_delete_ids).delete()

        # Update or create cells
        for cell_data in api_cells_data:
            cell_id = cell_data.get('id')
            if cell_id and Cell.objects.filter(id=cell_id, table_api=instance).exists():
                cell = Cell.objects.get(id=cell_id, table_api=instance)
                for key, value in cell_data.items():
                    setattr(cell, key, value)
                cell.save()
            else:
                Cell.objects.create(table_api=instance, **cell_data)
        return instance

# ----- PROJECT SERIALIZER -----


class TableCategorySerializerForJob(serializers.ModelSerializer):
    class Meta:
        model = TableCategory
        fields = [
            'id',
            'name',
            'order_number'
        ]


class TableCategorySerializer(serializers.ModelSerializer):
    tables = TableSerializer(many=True, read_only=True)

    class Meta:
        model = TableCategory
        fields = [
            'id',
            'name',
            'order_number',
            'tables'
        ]


class JobTableCollectionSerializer(serializers.ModelSerializer):
    table_categories = serializers.SerializerMethodField()

    class Meta:
        model = JobTableCollection
        fields = ['id', 'name', 'table_categories']

    def get_table_categories(self, obj):
        table_categories = obj.table_categories.all()
        return TableCategorySerializerForJob(table_categories, many=True).data

# ----- JOB SERIALIZER -----


class JobSerializer(serializers.ModelSerializer):
    # Read-only nested representation for related companies
    advisorCompanies = CompanySerializer(many=True, read_only=True)
    contractorCompanies = CompanySerializer(many=True, read_only=True)

    # Nested representation for JobTableCollection
    job_table_collection = JobTableCollectionSerializer(read_only=True)

    # Write-only fields for accepting company IDs
    advisorCompanies_ids = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), many=True, source='advisorCompanies', write_only=True
    )
    contractorCompanies_ids = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), many=True, source='contractorCompanies', write_only=True
    )

    # Example additional field
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id', 'name', 'created_at', 'progress',
            'advisorCompanies', 'advisorCompanies_ids',
            'contractorCompanies', 'contractorCompanies_ids',
            'description', 'due_date', 'priority', 'status',
            'job_table_collection'
        ]

    def get_progress(self, obj):
        return obj.table_apis.count()

    def create(self, validated_data):
        # Extract many-to-many data for companies
        advisor_companies = validated_data.pop('advisorCompanies', [])
        contractor_companies = validated_data.pop('contractorCompanies', [])
        job = Job.objects.create(**validated_data)
        job.advisorCompanies.set(advisor_companies)
        job.contractorCompanies.set(contractor_companies)
        return job

    def update(self, instance, validated_data):
        advisor_companies = validated_data.pop('advisorCompanies', None)
        contractor_companies = validated_data.pop('contractorCompanies', None)
        instance = super().update(instance, validated_data)
        if advisor_companies is not None:
            instance.advisorCompanies.set(advisor_companies)
        if contractor_companies is not None:
            instance.contractorCompanies.set(contractor_companies)
        return instance

# ----- PROJECT SERIALIZER -----


class ProjectSerializer(serializers.ModelSerializer):
    # Nested representation of the Company; for writes, use company_id
    company = CompanySerializer(read_only=True)
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), source='company', write_only=True
    )
    jobs = JobSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'created_at', 'company', 'company_id',
                  'description', 'start_date', 'end_date', 'status', 'budget', 'jobs']

#  ------------ excel upload ------------


logger = logging.getLogger(__name__)


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    table_id = serializers.UUIDField(required=True)
    column_ids = serializers.JSONField(required=True)
    job_id = serializers.UUIDField(required=False)
    strict_numeric = serializers.BooleanField(default=True)

    def validate_column_ids(self, value):
        logger.debug(f"Raw column_ids: {value}")
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError(
                "column_ids must be a non-empty list of UUIDs")
        try:
            cleaned_ids = [serializers.UUIDField().to_internal_value(
                cid.strip()) for cid in value]
            logger.debug(f"Cleaned column_ids: {cleaned_ids}")
            return cleaned_ids
        except ValidationError as e:
            logger.error(f"Invalid UUID in column_ids: {value}")
            raise serializers.ValidationError(f"Invalid UUID: {str(e)}")

    def validate(self, data):
        table_id = data.get('table_id')
        column_ids = data.get('column_ids')
        if not Table.objects.filter(id=table_id).exists():
            raise ValidationError(f"Table with id {table_id} does not exist")
        columns = Column.objects.filter(id__in=column_ids, table_id=table_id)
        if columns.count() != len(column_ids):
            invalid_ids = set(column_ids) - \
                set(columns.values_list('id', flat=True))
            raise ValidationError(
                f"Invalid column_ids: {invalid_ids} do not belong to table {table_id}")
        return data
