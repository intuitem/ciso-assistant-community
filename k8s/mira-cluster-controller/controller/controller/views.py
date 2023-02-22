from django.shortcuts import render
from controller.models import Client


def client_index(request):

    clients = Client.objects.all()

    context = {

        'clients': clients

    }

    return render(request, 'client_index.html', context)

