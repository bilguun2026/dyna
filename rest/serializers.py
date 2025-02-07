from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import (
    User, Company, Project, Job,
    Table, Column, Option, TableApi, Cell
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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

    class Meta:
        model = Column
        fields = ['id', 'name', 'data_type', 'options']

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


# ----- CELL SERIALIZER -----
class CellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cell
        fields = ['id', 'column', 'value', 'file', 'image', 'created_at']

    def validate(self, data):
        column = data.get('column')
        if column.data_type == 'select':
            options = [option.value for option in column.options.all()]
            value = data.get('value')
            if value not in options:
                raise serializers.ValidationError({
                    'value': f"Value '{value}' is not a valid option for column '{column.name}'."
                })
        return data


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

        # Remove cells that are not in the incoming data.
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


# ----- JOB SERIALIZER -----
class JobSerializer(serializers.ModelSerializer):
    advisorCompanies = CompanySerializer(many=True, read_only=True)
    contractorCompanies = CompanySerializer(many=True, read_only=True)
    # ... and write-only fields to accept lists of IDs.
    advisorCompanies_ids = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), many=True, source='advisorCompanies', write_only=True
    )
    contractorCompanies_ids = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), many=True, source='contractorCompanies', write_only=True
    )
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id', 'name', 'created_at',
            'progress',
            'advisorCompanies', 'advisorCompanies_ids',
            'contractorCompanies', 'contractorCompanies_ids', 'description',
            'due_date', 'priority', 'status'
        ]

    def get_progress(self, obj):
        completed_steps = obj.table_apis.count()
        return completed_steps

    def create(self, validated_data):
        # Pop off many-to-many data from the validated data
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


class ProjectSerializer(serializers.ModelSerializer):
    # Nested representation of the Company; for writes, use company_id.
    company = CompanySerializer(read_only=True)
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), source='company', write_only=True
    )
    jobs = JobSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'created_at', 'company', 'company_id',
                  'description', 'start_date', 'end_date', 'status', 'budget', 'jobs']
