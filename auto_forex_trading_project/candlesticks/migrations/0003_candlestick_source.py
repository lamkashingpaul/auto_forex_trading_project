# Generated by Django 3.2.4 on 2021-06-27 15:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('candlesticks', '0002_alter_candlestick_symbol'),
    ]

    operations = [
        migrations.AddField(
            model_name='candlestick',
            name='source',
            field=models.CharField(choices=[('Pandas', 'Pandas'), ('Dukascopy', 'Dukascopy')], default='Pandas', max_length=16, verbose_name='Source'),
        ),
    ]
