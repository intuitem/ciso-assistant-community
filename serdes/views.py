from django.views.generic import ListView, DetailView


class SerializedObjectListView(ListView):
    '''
    List view for serialized objects.
    '''
    # TODO: implement
    pass


class SerializedObjectDetailView(DetailView):
    '''
    Detail view for serialized objects.
    '''
    # TODO: implement
    
    def download(self):
        '''
        Download serialized object.
        '''
        pass


class SerializedObjectCreateView(CreateView):
    '''
    Create view for serialized objects.
    '''
    # TODO: implement
    pass
