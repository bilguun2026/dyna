from .forms import TableSelectionForm
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.forms import BaseInlineFormSet
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.shortcuts import render, redirect

from .models import (
    JobTableCollection, TableCategory, User, Table, Column, TableApi, Cell, Option,
    Company, Project, Job, File, Image
)

# -------------------------------------------------------------------------------
# TableCategory Admin
# -------------------------------------------------------------------------------


@admin.register(TableCategory)
class TableCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')  # columns visible in the admin list page
    search_fields = ('name',)

# -------------------------------------------------------------------------------
# JobTableCollection Admin
# -------------------------------------------------------------------------------


@admin.register(JobTableCollection)
class JobTableCollectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

# -------------------------------------------------------------------------------
# Option Inline Admin (for managing Option objects within a Column)
# -------------------------------------------------------------------------------


class OptionInline(admin.TabularInline):
    model = Option
    extra = 1  # Number of extra forms to show

# -------------------------------------------------------------------------------
# Column Admin
# -------------------------------------------------------------------------------


class ColumnAdmin(admin.ModelAdmin):
    list_display = ('name', 'data_type', 'table')
    search_fields = ('name', 'data_type')
    list_filter = ('data_type',)
    inlines = [OptionInline]


# Unregister Column first if it's already registered to prevent duplication.
if Column in admin.site._registry:
    admin.site.unregister(Column)
admin.site.register(Column, ColumnAdmin)

# -------------------------------------------------------------------------------
# Custom User Admin
# -------------------------------------------------------------------------------


class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('phone', 'role')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('phone', 'role')}),
    )


admin.site.register(User, CustomUserAdmin)

# -------------------------------------------------------------------------------
# Column Inline for Table (to show related columns in the Table admin)
# -------------------------------------------------------------------------------


class ColumnInline(admin.TabularInline):
    model = Column
    extra = 1  # Controls how many extra rows are displayed

# -------------------------------------------------------------------------------
# Cell Inline FormSet & Inline for TableApi
# -------------------------------------------------------------------------------


class CellInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        return super().save_new(form, commit=commit)

    def save_existing(self, form, instance, commit=True):
        return super().save_existing(form, instance, commit=commit)


class CellInline(admin.TabularInline):
    model = Cell
    extra = 0  # Show only existing data

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Check if we're in the add view and a table is selected via GET param
        table_id = request.GET.get('table')
        if table_id:
            table = Table.objects.get(pk=table_id)
            # Create the TableApi instance if not yet created
            table_api, created = TableApi.objects.get_or_create(
                table=table, user=request.user
            )
            # Return cells related to the selected table's API
            return Cell.objects.filter(table_api=table_api)
        return qs

# -------------------------------------------------------------------------------
# Table Admin
# -------------------------------------------------------------------------------


class TableAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    inlines = [ColumnInline]
    search_fields = ('name',)
    list_filter = ('created_at',)

    def response_add(self, request, obj, post_url_continue=None):
        return super().response_add(request, obj, post_url_continue)


admin.site.register(Table, TableAdmin)

# -------------------------------------------------------------------------------
# TableApi Admin with Custom Table Selection
# -------------------------------------------------------------------------------


class TableApiAdmin(admin.ModelAdmin):
    inlines = [CellInline]
    change_form_template = "admin/rest/table_api_change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('select-table/', self.admin_site.admin_view(self.select_table),
                 name='rest_tableapi_select_table'),
        ]
        return custom_urls + urls

    def select_table(self, request):
        """Custom view for table selection before proceeding to create TableApi."""
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
            form.base_fields['table'].initial = table
        return form

    def add_view(self, request, form_url='', extra_context=None):
        """Ensure user selects a table before proceeding to TableApi creation."""
        if 'table' not in request.GET:
            return HttpResponseRedirect(reverse('admin:rest_tableapi_select_table'))
        extra_context = extra_context or {}
        extra_context['table_id'] = request.GET['table']
        return super().add_view(request, form_url, extra_context)


admin.site.register(TableApi, TableApiAdmin)

# -------------------------------------------------------------------------------
# Inlines for File and Image models
# -------------------------------------------------------------------------------


class FileInline(admin.TabularInline):
    model = File
    extra = 0


class ImageInline(admin.TabularInline):
    model = Image
    extra = 0

# -------------------------------------------------------------------------------
# Cell Admin (Updated to include File and Image inlines)
# -------------------------------------------------------------------------------


class CellAdmin(admin.ModelAdmin):
    list_display = ('display_table_api', 'column', 'display_value')
    search_fields = ('column__name', 'value')
    list_filter = ('column__data_type',)
    inlines = [FileInline, ImageInline]

    def display_table_api(self, obj):
        return f"{obj.table_api.table.name} - {obj.table_api.user.username}"
    display_table_api.short_description = 'Table API'

    def display_value(self, obj):
        # For file or image types, show a preview or download link.
        if obj.column.data_type == 'image' and obj.images.exists():
            final_image = obj.images.all()[0]
            return format_html('<img src="{}" width="50" height="50"/>', final_image.image.url)
        elif obj.column.data_type == 'file' and obj.files.exists():
            final_file = obj.files.all()[0]
            return format_html('<a href="{}">Download File</a>', final_file.file.url)
        return obj.value
    display_value.short_description = 'Value'


admin.site.register(Cell, CellAdmin)

# -------------------------------------------------------------------------------
# File and Image Admin (Standalone registrations)
# -------------------------------------------------------------------------------


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('id', 'cell', 'file', 'uploaded_at')
    search_fields = ('cell__id', 'file')


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'cell', 'image', 'uploaded_at')
    search_fields = ('cell__id', 'image')

# -------------------------------------------------------------------------------
# Company Admin
# -------------------------------------------------------------------------------


class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


admin.site.register(Company, CompanyAdmin)

# -------------------------------------------------------------------------------
# Project Admin
# -------------------------------------------------------------------------------


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'created_at')
    search_fields = ('name',)
    list_filter = ('company', 'created_at')
    ordering = ('name',)


admin.site.register(Project, ProjectAdmin)

# -------------------------------------------------------------------------------
# Job Admin
# -------------------------------------------------------------------------------


class JobAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'project',
        'created_at',
        'get_advisor_companies',
        'get_contractor_companies'
    )
    search_fields = ('name',)
    list_filter = ('project', 'created_at')
    ordering = ('name',)
    filter_horizontal = ('advisorCompanies', 'contractorCompanies',)

    def get_advisor_companies(self, obj):
        return ", ".join([company.name for company in obj.advisorCompanies.all()])
    get_advisor_companies.short_description = "Advisor Companies"

    def get_contractor_companies(self, obj):
        return ", ".join([company.name for company in obj.contractorCompanies.all()])
    get_contractor_companies.short_description = "Contractor Companies"


admin.site.register(Job, JobAdmin)
