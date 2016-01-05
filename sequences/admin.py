from django.contrib import admin

from . import models


@admin.register(models.Sequence)
class Sequence(admin.ModelAdmin):

    list_display = ['name', 'last']
    ordering = ['name']
    search_fields = ['name']
