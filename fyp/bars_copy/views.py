from django.http import HttpResponse
from django.template import loader

from .models import Bar

def index(request):
    query_results = Bar.objects.all().order_by('time')
    template = loader.get_template('bars/index.html')
    context = {
        'query_results': query_results,
    }
    return HttpResponse(template.render(context, request))
