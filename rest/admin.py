from .forms import TableSelectionForm
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.forms import BaseInlineFormSet
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.shortcuts import render
from django.contrib import messages
from django import forms
from .utils import parse_formula, FormulaParseError
from .models import (
    JobTableCollection, TableCategory, User, Table, Column, TableApi, Cell, Option,
    Company, Project, Job, File, Image, Operation, FormulaStep, FormulaOperand
)


class ColumnAdminForm(forms.ModelForm):
    selected_columns = forms.MultipleChoiceField(
        choices=[],
        widget=forms.SelectMultiple(
            attrs={'id': 'id_selected_columns', 'style': 'display:none;'}),
        required=False
    )

    class Meta:
        model = Column
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        table = cleaned_data.get('table')
        if not table:
            raise forms.ValidationError("The 'Table' field is required.")
        return cleaned_data

    def clean_formula_text(self):
        formula_text = self.cleaned_data.get('formula_text', '')
        if formula_text and self.instance.table_id:
            valid_columns = set(Column.objects.filter(
                table=self.instance.table).values_list('name', flat=True))
            operations_dict = {op.name: op for op in Operation.objects.all()}
            try:
                tokens = parse_formula(
                    formula_text, self.instance, operations_dict)
                for token in tokens:
                    if isinstance(token, str) and token not in operations_dict and token not in '()+-*/%' and token not in valid_columns:
                        raise forms.ValidationError(
                            f"Invalid column name: '{token}' not found in table.")
            except FormulaParseError as e:
                raise forms.ValidationError(f"Invalid formula: {str(e)}")
        return formula_text

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.table_id:
            columns = Column.objects.filter(
                table=self.instance.table).exclude(id=self.instance.id)
            column_choices = [(col.name, col.name) for col in columns]
            self.fields['selected_columns'].choices = column_choices
            self.fields['formula_text'].widget.attrs.update({
                'class': 'formula-input',
                'data-columns': ','.join(col[0] for col in column_choices),
                'data-functions': 'sqrt,%,add,subtract,multiply,divide',
                'placeholder': 'e.g., sqrt(Column1) + Column2 * 5'
            })


# TableCategory Admin


@admin.register(TableCategory)
class TableCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

# JobTableCollection Admin


@admin.register(JobTableCollection)
class JobTableCollectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

# Operation Admin


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol')
    search_fields = ('name',)

# Option Inline Admin


class OptionInline(admin.TabularInline):
    model = Option
    extra = 1

# FormulaStep Inline Admin (Read-Only for Display)


class FormulaStepInline(admin.TabularInline):
    model = FormulaStep
    extra = 0
    readonly_fields = ('display_step', 'column',
                       'operation', 'operand', 'order')
    can_delete = False

    def display_step(self, obj):
        operand_str = obj.operand.__str__() if obj.operand else "No Operand"
        op_str = obj.operation.symbol if obj.operation else ""
        return f"{operand_str} {op_str}"
    display_step.short_description = "Step"

    def has_add_permission(self, request, obj=None):
        return False

# FormulaStep Admin


@admin.register(FormulaStep)
class FormulaStepAdmin(admin.ModelAdmin):
    list_display = ('column', 'display_step', 'order')
    list_filter = ('order',)
    raw_id_fields = ('column', 'operand', 'operation')

    def display_step(self, obj):
        operand_str = obj.operand.__str__() if obj.operand else "No Operand"
        op_str = obj.operation.symbol if obj.operation else ""
        return f"{operand_str} {op_str}"
    display_step.short_description = "Step"

# Column Admin


class ColumnAdmin(admin.ModelAdmin):
    form = ColumnAdminForm
    list_display = ('name', 'data_type', 'table',
                    'formula_text', 'display_formula')
    search_fields = ('name', 'data_type')
    list_filter = ('data_type', 'table')
    inlines = [OptionInline, FormulaStepInline]
    actions = ['create_intermediate_columns_for_formula']
    change_form_template = 'admin/rest/column_change_form.html'

    class Media:
        css = {
            'all': ('admin/css/column_formula.css',)
        }
        js = ('admin/js/column_formula.js',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        print("Form fields:", form.base_fields.keys())  # Debug
        if obj and hasattr(obj, 'table_id') and obj.table_id:
            if 'formula_text' in form.base_fields:
                form.base_fields['formula_text'].initial = obj.formula_text
            kwargs['column_options'] = list(
                Column.objects.filter(table_id=obj.table_id).values('name'))
        else:
            table_id = request.GET.get('table')
            if table_id:
                try:
                    table = Table.objects.get(id=table_id)
                    form.initial['table'] = table
                    kwargs['column_options'] = list(
                        Column.objects.filter(table_id=table_id).values('name'))
                except Table.DoesNotExist:
                    kwargs['column_options'] = []
            else:
                kwargs['column_options'] = []
        return form

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if add:
            context['column_options'] = []
            table_id = request.GET.get('table')
            if table_id:
                context['table_id'] = table_id
        elif obj and obj.table_id:
            context['column_options'] = list(
                Column.objects.filter(table_id=obj.table_id).values('name'))
        else:
            context['column_options'] = []
        return super().render_change_form(request, context, add=add, change=change, form_url=form_url, obj=obj)

    def display_formula(self, obj):
        steps = FormulaStep.objects.filter(column=obj).order_by('order')
        if not steps.exists():
            return "-"
        formula_parts = []
        for step in steps:
            operand_str = step.operand.__str__() if step.operand else "No Operand"
            op_str = step.operation.symbol if step.operation else ""
            formula_parts.append(f"{operand_str} {op_str}")
        return " ".join(formula_parts)
    display_formula.short_description = "Parsed Formula"

    def create_intermediate_columns_for_formula(self, request, queryset):
        operations_dict = {op.name: op for op in Operation.objects.all()}
        for column in queryset:
            formula_text = column.formula_text
            if not formula_text:
                messages.warning(
                    request, f"Column {column.name} has no formula to process.")
                continue
            try:
                intermediate_cols = parse_formula(
                    formula_text, column, operations_dict)
                messages.success(
                    request, f"Created {len(intermediate_cols)} intermediate columns for {column.name}.")
            except FormulaParseError as e:
                messages.error(
                    request, f"Error processing formula for {column.name}: {str(e)}")

    create_intermediate_columns_for_formula.short_description = "Create intermediate columns for formula"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.formula_text and (change or not FormulaStep.objects.filter(column=obj).exists()):
            operations_dict = {op.name: op for op in Operation.objects.all()}
            try:
                FormulaStep.objects.filter(column=obj).delete()
                parse_formula(obj.formula_text, obj, operations_dict)
            except FormulaParseError as e:
                messages.error(
                    request, f"Error saving formula for {obj.name}: {str(e)}")


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

# Column Inline for Table


class ColumnInline(admin.TabularInline):
    model = Column
    extra = 1

# Cell Inline FormSet & Inline for TableApi


class CellInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        return super().save_new(form, commit=commit)

    def save_existing(self, form, instance, commit=True):
        return super().save_existing(form, instance, commit=commit)


class CellInline(admin.TabularInline):
    model = Cell
    extra = 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        table_id = request.GET.get('table')
        if table_id:
            table = Table.objects.get(pk=table_id)
            table_api, created = TableApi.objects.get_or_create(
                table=table, user=request.user
            )
            return Cell.objects.filter(table_api=table_api)
        return qs

# Table Admin


class TableAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    inlines = [ColumnInline]
    search_fields = ('name',)
    list_filter = ('created_at',)

    def response_add(self, request, obj, post_url_continue=None):
        return super().response_add(request, obj, post_url_continue)


admin.site.register(Table, TableAdmin)

# TableApi Admin with Custom Table Selection


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
        if request.method == 'POST':
            form = TableSelectionForm(request.POST)
            if form.is_valid():
                table_id = form.cleaned_data['table'].id
                return HttpResponseRedirect(reverse('admin:rest_tableapi_add') + f'?table={table_id}')
        else:
            form = TableSelectionForm()

        return render(request, "admin/rest/select_table.html", {'form': form})

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None and 'table' in request.GET:
            table_id = request.GET['table']
            table = Table.objects.get(pk=table_id)
            form.base_fields['table'].initial = table
        return form

    def add_view(self, request, form_url='', extra_context=None):
        if 'table' in request.GET:
            extra_context = extra_context or {}
            extra_context['table_id'] = request.GET['table']
            return super().add_view(request, form_url, extra_context)
        return HttpResponseRedirect(reverse('admin:rest_tableapi_select_table'))


admin.site.register(TableApi, TableApiAdmin)

# Inlines for File and Image models


class FileInline(admin.TabularInline):
    model = File
    extra = 0


class ImageInline(admin.TabularInline):
    model = Image
    extra = 0

# Cell Admin


class CellAdmin(admin.ModelAdmin):
    list_display = ('display_table_api', 'column',
                    'display_value', 'display_computed_value')
    search_fields = ('column__name', 'value')
    list_filter = ('column__data_type',)
    inlines = [FileInline, ImageInline]

    def display_table_api(self, obj):
        return f"{obj.table_api.table.name} - {obj.table_api.user.username}"
    display_table_api.short_description = 'Table API'

    def display_value(self, obj):
        if obj.column.data_type == 'image' and obj.images.exists():
            final_image = obj.images.all()[0]
            return format_html('<img src="{}" width="50" height="50"/>', final_image.image.url)
        elif obj.column.data_type == 'file' and obj.files.exists():
            final_file = obj.files.all()[0]
            return format_html('<a href="{}">Download File</a>', final_file.file.url)
        return obj.value
    display_value.short_description = 'Value'

    def display_computed_value(self, obj):
        if FormulaStep.objects.filter(column=obj.column).exists():
            return obj.computed_value
        return "-"
    display_computed_value.short_description = 'Computed Value'


admin.site.register(Cell, CellAdmin)

# File and Image Admin


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('id', 'cell', 'file', 'uploaded_at')
    search_fields = ('cell__id', 'file')


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'cell', 'image', 'uploaded_at')
    search_fields = ('cell__id', 'image')

# Company Admin


class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


admin.site.register(Company, CompanyAdmin)

# Project Admin


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'created_at')
    search_fields = ('name',)
    list_filter = ('company', 'created_at')
    ordering = ('name',)


admin.site.register(Project, ProjectAdmin)

# Job Admin


class JobAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'created_at',
                    'get_advisor_companies', 'get_contractor_companies')
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
