from django import forms
from .models import Candlestick
from datetime import timedelta

from uuid import UUID

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

price_type_input_attrs = {
    'class': 'form-control',
}

sma_crossover_fast_ma_period_input_attrs = {

}

sma_crossover_slow_ma_period_input_attrs = {

}


class HistoryForm(forms.Form):
    symbol = forms.ChoiceField(choices=Candlestick.SYMBOLS, widget=forms.Select(attrs=symbol_input_attrs))
    date_from = forms.DateTimeField(input_formats=['%d/%m/%Y'], widget=forms.DateTimeInput(attrs=date_from_input_attrs))
    date_before = forms.DateTimeField(input_formats=['%d/%m/%Y'], widget=forms.DateTimeInput(attrs=date_before_input_attrs))
    period = forms.TypedChoiceField(choices=Candlestick.PERIODS, widget=forms.Select(attrs=period_input_attrs), coerce=int)
    price_type = forms.ChoiceField(choices=Candlestick.PRICE_TYPES, widget=forms.Select(attrs=price_type_input_attrs))
    source = forms.ChoiceField(choices=Candlestick.SOURCES, widget=forms.Select(attrs=source_input_attrs))

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_before = cleaned_data.get('date_before')
        if not (date_from < date_before):
            raise forms.ValidationError('Start time must be before end time.')
        cleaned_data['date_before'] += timedelta(microseconds=-1)
        return cleaned_data


class SMACrossoverForm(forms.Form):
    sma_crossover_fast_ma_period = forms.IntegerField(min_value=2)
    sma_crossover_slow_ma_period = forms.IntegerField(min_value=3)
    number_of_bars = forms.IntegerField(min_value=4)

    def clean(self):
        cleaned_data = super().clean()
        sma_crossover_fast_ma_period = cleaned_data.get('sma_crossover_fast_ma_period')
        sma_crossover_slow_ma_period = cleaned_data.get('sma_crossover_slow_ma_period')
        number_of_bars = cleaned_data.get('number_of_bars')
        if not (1 < sma_crossover_fast_ma_period < sma_crossover_slow_ma_period < number_of_bars):
            raise forms.ValidationError('Invalid input periods.')
        return cleaned_data


class TaskIDForm(forms.Form):
    task_id = forms.CharField()

    def clean(self):
        cleaned_data = super().clean()
        task_id = cleaned_data.get('task_id')
        try:
            UUID(task_id, version=4)
        except ValueError:
            return False
        return cleaned_data
