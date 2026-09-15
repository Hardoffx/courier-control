from django import forms
from .models import Delivery

class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ('delivery_date','address','organization','recipient','phone','comment','courier','route_order','status')
        widgets = {'delivery_date': forms.DateInput(attrs={'type':'date'}), 'comment': forms.Textarea(attrs={'rows':2})}
