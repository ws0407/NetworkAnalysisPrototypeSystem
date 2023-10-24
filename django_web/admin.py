from django.contrib import admin
from django_web import models

# Register your models here.

admin.site.register(models.Job)
admin.site.register(models.Driver)
admin.site.register(models.Function)
admin.site.register(models.Function_Driver)
