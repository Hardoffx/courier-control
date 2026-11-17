from django import forms
from .models import Delivery, DeliveryPoint
from accounts.models import User

class DeliveryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['courier'].queryset = User.objects.filter(role=User.Role.COURIER, is_superuser=False, is_active=True, archived_at__isnull=True)

    class Meta:
        model = Delivery
        fields = ('delivery_date','source_label','address','organization','recipient','phone','comment','time_window','row_color','courier','route_order','status')
        labels = {'source_label':'Объект / код','time_window':'Временное окно','row_color':'Цвет строки'}
        widgets = {'delivery_date': forms.DateInput(attrs={'type':'date'}), 'comment': forms.Textarea(attrs={'rows':2})}

class DeliveryPointForm(forms.ModelForm):
    class Meta:
        model = DeliveryPoint
        fields = ('name','code','address','kind','phone','is_active')
        labels = {'name':'Название / обозначение','code':'Код CMD','address':'Канонический адрес','kind':'Тип точки','phone':'Телефон','is_active':'Активна'}
