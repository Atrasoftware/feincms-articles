from django.conf import settings
from django.core.urlresolvers import get_callable
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.conf.urls import patterns, url
from django.utils.encoding import python_2_unicode_compatible

from feincms.admin import item_editor, tree_editor
from feincms.content.application import models as app_models
from feincms.models import create_base_model
from feincms.module.mixins import ContentModelMixin
from feincms.utils.managers import ActiveAwareContentManagerMixin

from mptt.models import MPTTModel, TreeManager
from .forms import ArticleAdminForm


class ArticleManager(ActiveAwareContentManagerMixin, TreeManager):
    active_filters = {'simple-active': Q(active=True)}

    # The fields which should be excluded when creating a copy.
    exclude_from_copy = [
        'id', 'tree_id', 'lft', 'rght', 'level', 'redirect_to']


@python_2_unicode_compatible
class BaseArticle(create_base_model(MPTTModel), ContentModelMixin):
    active = models.BooleanField(_('active'), default=True)

    title = models.CharField(_('title'), max_length=255)
    slug = models.SlugField(
        _('slug'),
        max_length=255,
        help_text=_('This will be automatically generated from the name'),
        unique=True,
        editable=True,
    )

    parent = models.ForeignKey(
        'self', verbose_name=_('Parent'), blank=True,
        null=True, related_name='children')
    # Custom list_filter - see admin/filterspecs.py
    parent.parent_filter = True

    class Meta:
        ordering = ['title']
        unique_together = []
        verbose_name = _('article')
        verbose_name_plural = _('articles')
        abstract = True

    objects = ArticleManager()

    @classmethod
    def get_urlpatterns(cls):
        import views
        return patterns('',
            url(r'^$', views.ArticleList.as_view(), name='article_index'),
            url(r'^(?P<slug>[a-z0-9_-]+)/$', views.ArticleDetail.as_view(), name='article_detail'),
        )

    @classmethod
    def remove_field(cls, f_name):
        """Remove a field. Effectively inverse of contribute_to_class"""
        # Removes the field form local fields list
        cls._meta.local_fields = [f for f in cls._meta.local_fields if f.name != f_name]

        # Removes the field setter if exists
        if hasattr(cls, f_name):
            delattr(cls, f_name)

    @classmethod
    def get_urls(cls):
        return cls.get_urlpatterns()

    def __str__(self):
        return self.title

    @app_models.permalink
    def get_absolute_url(self):
        return ('article_detail', 'articles.urls', (), {'slug': self.slug})

    @property
    def is_active(self):
        return self.__class__.objects.active().filter(pk=self.pk).count() > 0


ExtensionModelAdmin = get_callable(getattr(
    settings, 'ARTICLE_MODELADMIN_CLASS', 'feincms.extensions.ExtensionModelAdmin'))


class ArticleAdmin(item_editor.ItemEditor, tree_editor.TreeEditor, ExtensionModelAdmin):

    form = ArticleAdminForm

    list_display = ['title', 'active']
    list_filter = []
    search_fields = ['title', 'slug']
    filter_horizontal = []
    prepopulated_fields = {
        'slug': ('title',),
    }

    fieldset_insertion_index = 2
    fieldsets = [
        (None, {
            'fields': [
                ('title', 'slug'),
                ('active',),
            ],
        }),
        (_('Other options'), {
            'classes': ['collapse'],
            'fields': ['parent'],
        }),
        # <-- insertion point, extensions appear here, see insertion_index
        # above
        item_editor.FEINCMS_CONTENT_FIELDSET,
    ]
