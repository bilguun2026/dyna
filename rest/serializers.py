from optparse import Option
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import User, Table, Column, TableApi, Cell
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


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


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'value']


class ColumnSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()

    class Meta:
        model = Column
        fields = ['id', 'name', 'data_type', 'options']

    def get_options(self, obj):
        if obj.data_type == 'select':
            options = Option.objects.filter(column=obj)
            return OptionSerializer(options, many=True).data
        return None


class TableSerializer(serializers.ModelSerializer):
    columns = ColumnSerializer(many=True, read_only=True)

    class Meta:
        model = Table
        fields = ['id', 'name', 'created_at', 'columns']


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


class TableApiSerializer(serializers.ModelSerializer):
    api_cells = CellSerializer(many=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = TableApi
        fields = ['id', 'table', 'user', 'api_cells', 'children']

    def get_children(self, obj):
        # This method fetches and serializes child TableApis
        # Using the related name 'children' set in the ForeignKey
        children = obj.children.all()
        # Recursive serialization
        return TableApiSerializer(children, many=True).data

    def create(self, validated_data):
        api_cells_data = validated_data.pop(
            'api_cells', [])  # Fix related name
        table_api = TableApi.objects.create(**validated_data)

        # Bulk create cells related to the TableApi instance
        cell_instances = [Cell(table_api=table_api, **cell_data)
                          for cell_data in api_cells_data]
        Cell.objects.bulk_create(cell_instances)

        return table_api

    def update(self, instance, validated_data):
        api_cells_data = validated_data.pop(
            'api_cells', [])  # Fix related name

        # Update main instance fields
        instance.table = validated_data.get('table', instance.table)
        instance.user = validated_data.get('user', instance.user)
        instance.save()

        # Get existing related cells
        existing_ids = set(instance.api_cells.values_list('id', flat=True))
        incoming_ids = {cell_data.get(
            'id') for cell_data in api_cells_data if 'id' in cell_data}

        # DELETE: Remove old cells that are not in the incoming data
        to_delete_ids = existing_ids - incoming_ids
        Cell.objects.filter(id__in=to_delete_ids).delete()

        # UPDATE / CREATE: Process incoming cell data
        new_cells = []
        for cell_data in api_cells_data:
            cell_id = cell_data.get('id')
            if cell_id and Cell.objects.filter(id=cell_id).exists():
                cell = Cell.objects.get(id=cell_id, table_api=instance)
                for key, value in cell_data.items():
                    setattr(cell, key, value)
                cell.save()
            else:
                new_cells.append(Cell(table_api=instance, **cell_data))

        # Bulk create new cells (optimized for performance)
        if new_cells:
            Cell.objects.bulk_create(new_cells)

        return instance
