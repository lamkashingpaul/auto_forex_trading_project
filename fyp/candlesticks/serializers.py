from rest_framework import serializers
from .models import Candlestick


class CandlestickSerializer(serializers.ModelSerializer):
    time = serializers.DateTimeField(read_only=True)
    open = serializers.FloatField(read_only=True)
    high = serializers.FloatField(read_only=True)
    low = serializers.FloatField(read_only=True)
    close = serializers.FloatField(read_only=True)
    volume = serializers.FloatField(read_only=True)

    class Meta:
        model = Candlestick
        fields = (
            'time',
            'open',
            'high',
            'low',
            'close',
            'volume',
        )
