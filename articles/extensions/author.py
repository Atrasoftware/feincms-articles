import warnings

from django.contrib.gis import admin
from django import models
from django.utils.translation import ugettext_lazy as _
from feincms import extensions


class Extension(extensions.Extension):
    """
    Adds a field to save the article author

    TODO: if the field is empty, auto add
    the current logged in user. Should be a FK
    """

    def handle_model(self):
        self.model.add_to_class(
            'author',
            models.CharField(
                verbose_name=_('author'),
                null=True,
                blank=True)
        )

    def handle_modeladmin(self, modeladmin):

        modeladmin.add_extension_options(_('Author'), {
            'fields': ('author',),
            'classes': ('collapse',),
        })
