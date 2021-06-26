from django.db import models

# Create your models here.
class Symbol(models.Model):
    symbol = models.CharField('Symbol', max_length=7)

    def __str__(self):
        return self.symbol

class Bar(models.Model):
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE)
    time = models.DateTimeField('Datetime', unique=True)
    open = models.FloatField('Open')
    high = models.FloatField('High')
    low = models.FloatField('Low')
    close = models.FloatField('Close')
    volume = models.FloatField('Volume')

    def __str__(self):
        return ''.join((self.symbol.symbol, ' ' ,str(self.time)))
