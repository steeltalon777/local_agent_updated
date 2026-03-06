from django import forms

from .models import Category, Item, Operation, OperationType, Site


class OperationForm(forms.Form):
    operation_type = forms.ChoiceField(choices=OperationType.choices, label='Тип операции')
    item_id = forms.ModelChoiceField(queryset=Item.objects.none(), label='ТМЦ')
    serial = forms.CharField(required=False, label='Серийный номер')
    quantity = forms.FloatField(min_value=0.0001, initial=1, label='Количество')
    receiver_name = forms.CharField(required=False, label='Получатель')
    vehicle = forms.CharField(required=False, label='Транспорт')
    comment = forms.CharField(required=False, widget=forms.Textarea, label='Комментарий')
    from_site = forms.ModelChoiceField(queryset=Site.objects.none(), required=False, label='Откуда')
    to_site = forms.ModelChoiceField(queryset=Site.objects.none(), required=False, label='Куда')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item_id'].queryset = Item.objects.filter(is_active=True).order_by('name')
        self.fields['from_site'].queryset = Site.objects.filter(is_active=True).order_by('name')
        self.fields['to_site'].queryset = Site.objects.filter(is_active=True).order_by('name')


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'sku', 'category', 'default_unit', 'is_active']


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent', 'is_active']


class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = ['name', 'code', 'is_active']


class OperationFilterForm(forms.Form):
    q = forms.CharField(required=False, label='Поиск')
    operation_type = forms.ChoiceField(required=False, choices=[('', 'Все типы'), *OperationType.choices])
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
