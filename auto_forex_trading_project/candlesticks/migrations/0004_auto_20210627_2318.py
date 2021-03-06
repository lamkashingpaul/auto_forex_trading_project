# Generated by Django 3.2.4 on 2021-06-27 15:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('candlesticks', '0003_candlestick_source'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='candlestick',
            name='one_candlestick_per_timeframe',
        ),
        migrations.AddConstraint(
            model_name='candlestick',
            constraint=models.UniqueConstraint(fields=('symbol', 'time', 'period', 'source'), name='one_candlestick_per_timeframe_per_source'),
        ),
    ]
