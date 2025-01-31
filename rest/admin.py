from .forms import TableSelectionForm
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.forms import BaseInlineFormSet
from django.utils.html import format_html
from .models import User, Table, Column, TableApi, Cell, Option
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import render, redirect
from django.urls import reverse
# Option Inline Admin


class OptionInline(admin.TabularInline):
    model = Option
    extra = 1  # Number of extra forms to show

# Column Admin


class ColumnAdmin(admin.ModelAdmin):
    list_display = ('name', 'data_type', 'table')
    search_fields = ('name', 'data_type')
    list_filter = ('data_type',)
    inlines = [OptionInline]


# Unregister Column first if it's already registered to prevent duplication
if Column in admin.site._registry:
    admin.site.unregister(Column)
admin.site.register(Column, ColumnAdmin)

# Custom User Admin


class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('phone', 'role')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('phone', 'role')}),
    )


admin.site.register(User, CustomUserAdmin)

# Column Inline Admin for Table


class ColumnInline(admin.TabularInline):
    model = Column
    extra = 1  # Controls how many extra rows are displayed

# Inline admin for Cells within TableApi


class CellInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        # This is called to save objects for new forms in the formset
        return super().save_new(form, commit=commit)

    def save_existing(self, form, instance, commit=True):
        # This is called to save objects for existing forms in the formset
        return super().save_existing(form, instance, commit=commit)


class CellInline(admin.TabularInline):
    model = Cell
    extra = 0  # Don't add extra empty fields, only show real data

    def get_queryset(self, request):
        """Ensure that when a TableApi is created, its cells appear automatically."""
        qs = super().get_queryset(request)

        # Check if we're in the "add" view and a table is selected
        table_id = request.GET.get('table')
        if table_id:
            table = Table.objects.get(pk=table_id)

            # Create the TableApi instance if not yet created
            table_api, created = TableApi.objects.get_or_create(
                table=table, user=request.user)
            # Ensure missing cells are created

            # Fetch and return the related cells for the selected table
            return Cell.objects.filter(table_api=table_api)

        return qs


# Admin for Table


class TableAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    inlines = [ColumnInline]
    search_fields = ('name',)
    list_filter = ('created_at',)

    def response_add(self, request, obj, post_url_continue=None):
        return super().response_add(request, obj, post_url_continue)


admin.site.register(Table, TableAdmin)

# Admin for TableApi


class TableApiAdmin(admin.ModelAdmin):
    inlines = [CellInline]
    change_form_template = "admin/rest/table_api_change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('select-table/', self.admin_site.admin_view(self.select_table),
                 name='rest_tableapi_select_table'),
        ]
        return custom_urls + urls  # Ensures custom URLs appear first

    def select_table(self, request):
        """Custom view for table selection before proceeding to create TableApi"""
        if request.method == 'POST':
            form = TableSelectionForm(request.POST)
            if form.is_valid():
                table_id = form.cleaned_data['table'].id
                return HttpResponseRedirect(reverse('admin:rest_tableapi_add') + f'?table={table_id}')
        else:
            form = TableSelectionForm()

        return render(request, "admin/rest/select_table.html", {'form': form})

    def get_form(self, request, obj=None, **kwargs):
        """Pre-fill the Table field when creating a new TableApi."""
        form = super().get_form(request, obj, **kwargs)

        if obj is None and 'table' in request.GET:
            table_id = request.GET['table']
            table = Table.objects.get(pk=table_id)
            form.base_fields['table'].initial = table  # Auto-fill table field

        return form

    def add_view(self, request, form_url='', extra_context=None):
        """Ensure user selects a table before proceeding to TableApi creation."""
        if 'table' not in request.GET:
            # Redirect to table selection
            return HttpResponseRedirect(reverse('admin:rest_tableapi_select_table'))

        extra_context = extra_context or {}
        extra_context['table_id'] = request.GET['table']
        return super().add_view(request, form_url, extra_context)


admin.site.register(TableApi, TableApiAdmin)


class CellAdmin(admin.ModelAdmin):
    list_display = ('display_table_api', 'column', 'display_value')
    search_fields = ('column__name', 'value')
    list_filter = ('column__data_type',)

    def display_table_api(self, obj):
        return f"{obj.table_api.table.name} - {obj.table_api.user.username}"
    display_table_api.short_description = 'Table API'

    def display_value(self, obj):
        if obj.column.data_type == 'image' and obj.image:
            return format_html('<img src="{}" width="50" height="50"/>', obj.image.url)
        elif obj.column.data_type == 'file' and obj.file:
            return format_html('<a href="{}">Download File</a>', obj.file.url)
        return obj.value
    display_value.short_description = 'Value'


admin.site.register(Cell, CellAdmin)
