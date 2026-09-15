from django import forms
from .models import Delivery

class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ('delivery_date','source_label','address','organization','recipient','phone','comment','time_window','row_color','courier','route_order','status')
        labels = {'source_label':'Объект / код','time_window':'Временное окно','row_color':'Цвет строки'}
        widgets = {'delivery_date': forms.DateInput(attrs={'type':'date'}), 'comment': forms.Textarea(attrs={'rows':2})}
