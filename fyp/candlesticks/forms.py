from django import forms
from .models import Candlestick
import datetime

symbol_input_attrs = {
    'class': 'form-control',
}

start_time_input_attrs = {
    'class': 'form-control',
    'type': 'text',
    'autocomplete': 'off',
    'placeholder': 'Start time'

}

end_time_input_attrs = {
    'class': 'form-control',
    'type': 'text',
    'autocomplete': 'off',
    'placeholder': 'End time'
}

macd_fast_ma_period_input_attrs ={

}

macd_slow_ma_period_input_attrs ={

}

class HistoryForm(forms.Form):
    symbol = forms.ChoiceField(choices=Candlestick.SYMBOLS, widget=forms.Select(attrs=symbol_input_attrs))
    start_time = forms.DateTimeField(input_formats=['%d/%m/%Y'], widget=forms.DateTimeInput(attrs=start_time_input_attrs))
    end_time = forms.DateTimeField(input_formats=['%d/%m/%Y'], widget=forms.DateTimeInput(attrs=end_time_input_attrs))

    def clean(self):
        cleaned_data = super().clean()
        symbol = cleaned_data.get('symbol')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if not (start_time < end_time):
            raise forms.ValidationError('Start time must be before end time.')
        pass

class MACDForm(forms.Form):
    macd_fast_ma_period = forms.IntegerField(min_value=2)
    macd_slow_ma_period = forms.IntegerField(min_value=3)
    number_of_bars = forms.IntegerField(min_value=4)

    def clean(self):
        cleaned_data = super().clean()
        macd_fast_ma_period = cleaned_data.get('macd_fast_ma_period')
        macd_slow_ma_period = cleaned_data.get('macd_slow_ma_period')
        number_of_bars = cleaned_data.get('number_of_bars')
        if not (1 < macd_fast_ma_period < macd_slow_ma_period < number_of_bars):
            raise forms.ValidationError('Invalid input periods.')
        return cleaned_data
