from django.db import models
from controller.control import creatcreate_client_objects

class Client(models.Model):
    name = models.CharField(max_length=40)
    admin_email = models.EmailField()

    def save(self, *args, **kwargs):
        print("saving", self.name, self.admin_email)
        super().save(*args, **kwargs)  # Call the "real" save() method.
        print("creating k8s objects for", self.name)
        create_client_objects(self.name, self.admin_email)
