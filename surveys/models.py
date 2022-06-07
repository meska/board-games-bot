from django.db import models


# Create your models here.
class Survey(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    age = models.IntegerField()
