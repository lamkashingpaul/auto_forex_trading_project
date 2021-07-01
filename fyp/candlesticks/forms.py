from django import forms
from .models import Candlestick
from datetime import timedelta

symbol_input_attrs = {
    'class': 'form-control',
}

date_from_input_attrs = {
    'class': 'form-control',
    'type': 'text',
    'autocomplete': 'off',
    'placeholder': 'Date from'

}

date_before_input_attrs = {
    'class': 'form-control',
    'type': 'text',
    'autocomplete': 'off',
    'placeholder': 'Date before'
}

period_input_attrs = {
    'class': 'form-control',
}

source_input_attrs = {
    'class': 'form-control',
}

macd_fast_ma_period_input_attrs = {

}

macd_slow_ma_period_input_attrs = {

}


class HistoryForm(forms.Form):
    symbol = forms.ChoiceField(choices=Candlestick.SYMBOLS, widget=forms.Select(attrs=symbol_input_attrs))
    date_from = forms.DateTimeField(input_formats=['%d/%m/%Y'], widget=forms.DateTimeInput(attrs=date_from_input_attrs))
    date_before = forms.DateTimeField(input_formats=['%d/%m/%Y'], widget=forms.DateTimeInput(attrs=date_before_input_attrs))
    period = forms.ChoiceField(choices=Candlestick.PERIODS, widget=forms.Select(attrs=period_input_attrs))
    source = forms.ChoiceField(choices=Candlestick.SOURCES, widget=forms.Select(attrs=source_input_attrs))

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_before = cleaned_data.get('date_before')
        if not (date_from < date_before):
            raise forms.ValidationError('Start time must be before end time.')
        cleaned_data['date_before'] += timedelta(microseconds=-1)
        return cleaned_data


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
