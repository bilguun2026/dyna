from django import forms
from .models import Table


class TableSelectionForm(forms.Form):
    table = forms.ModelChoiceField(
        queryset=Table.objects.all(), label="Select Table")
