from django.conf import settings
from django.core.urlresolvers import get_callable
from django.db import models
from django.db.models import Q
from django.utils.translation import get_language, ugettext_lazy as _
from django.conf.urls import patterns, url
from django.utils.encoding import python_2_unicode_compatible

from feincms.admin import item_editor, tree_editor
# from feincms.content.application import models as app_models
from feincms.models import create_base_model
from feincms.module.mixins import ContentModelMixin
from feincms.utils.managers import ActiveAwareContentManagerMixin

from mptt.models import MPTTModel, TreeManager
from .forms import ArticleAdminForm


############################
from feincms.content.application.models import ApplicationContent
from feincms.translations import short_language_code


class ArticlesApplicationContent(ApplicationContent):
    '''
    Custom Application Content (WIP)
    '''

    class Meta:
        abstract = True
        verbose_name = _('Articles application content')
        verbose_name_plural = _('Articles application contents')

    @classmethod
    def closest_match(cls, urlconf_path, page_slug=None):
        page_class = cls.parent.field.rel.to

        if page_slug:
            contents = cls.objects.filter(
                parent__in=page_class.objects.active(),
                parent__slug__exact=page_slug,
                urlconf_path=urlconf_path,
            ).order_by('pk').select_related('parent')
        else:
            contents = cls.objects.filter(
                parent__in=page_class.objects.active(),
                urlconf_path=urlconf_path,
            ).order_by('pk').select_related('parent')

        # import pdb; pdb.set_trace()

        if len(contents) > 1:
            try:
                current = short_language_code(get_language())
                return [
                    content for content in contents if
                    short_language_code(content.parent.language) == current
                ][0]

            except (AttributeError, IndexError):
                pass

        try:
            return contents[0]
        except IndexError:
            pass

        return None

from django.core.cache import cache
from django.core.urlresolvers import (
    Resolver404, resolve, reverse, NoReverseMatch)
from feincms.content.application.models import cycle_app_reverse_cache
from django.utils.functional import curry as lazy, wraps


def articles_app_reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=None, *vargs, **vkwargs):
    """
    Customized version of app_reverse, specialized for CustomApplicationContent
    It uses an additional keyword argument 'page_slug' to resolve application
    content absolute_url starting from page_slug.

    {% articles_app_reverse
        'article_category'
        request
        category_url=category.local_url
        page_slug=feincms_page.slug
        as
        custom_category_url
    %}
    """

    # First parameter might be a request instead of an urlconf path, so
    # we'll try to be helpful and extract the current urlconf from it
    extra_context = getattr(urlconf, '_feincms_extra_context', {})
    appconfig = extra_context.get('app_config', {})

    urlconf = appconfig.get('urlconf_path', urlconf)

    cache_generation = cache.get('app_reverse_cache_generation')
    if cache_generation is None:
        # This might never happen. Still, better be safe than sorry.
        cycle_app_reverse_cache()
        cache_generation = cache.get('app_reverse_cache_generation')

    cache_key = '%s-%s-%s-%s' % (
        urlconf,
        get_language(),
        getattr(settings, 'SITE_ID', 0),
        cache_generation)

    url_prefix = cache.get(cache_key)

    # FIXME: Bypass cache recovery; resolve does not retrieve right url.
    url_prefix = None

    # First time, the item get saved into cache
    if url_prefix is None:
        # Manage different ApplicationContent content type creation order
        try:
            appcontent_class = ArticlesApplicationContent._feincms_content_models[1]
        except:
            appcontent_class = ArticlesApplicationContent._feincms_content_models[0]

        # !!!!!!! If Content is None, NoReverseMatch is raised
        try:
            content = appcontent_class.closest_match(
                urlconf, kwargs['page_slug'])
            del kwargs['page_slug']
        except (KeyError, TypeError):
            content = appcontent_class.closest_match(urlconf)

        if content is not None:
            if urlconf in appcontent_class.ALL_APPS_CONFIG:
                # We have an overridden URLconf
                app_config = appcontent_class.ALL_APPS_CONFIG[urlconf]
                urlconf = app_config['config'].get('urls', urlconf)

            prefix = content.parent.get_absolute_url()
            prefix += '/' if prefix[-1] != '/' else ''

            url_prefix = (urlconf, prefix)

            # Save url_prefix into cache
            cache.set(cache_key, url_prefix)

    if url_prefix:
        # vargs and vkwargs are used to send through additional parameters
        # which are uninteresting to us (such as current_app)
        ret_value = reverse(
            viewname,
            url_prefix[0],
            args=args,
            kwargs=kwargs,
            prefix=url_prefix[1],
            *vargs, **vkwargs)
        return ret_value

    raise NoReverseMatch("Unable to find ApplicationContent for %r" % urlconf)

#: Lazy version of ``app_reverse``
articles_app_reverse_lazy = lazy(articles_app_reverse, str)


def articles_permalink(func):
    """
    Decorator that calls articles_app_reverse()

    Use this instead of standard django.db.models.permalink if you want to
    integrate the model through CustomApplicationContent. The wrapped function
    must return 4 instead of 3 arguments::

        class MyModel(models.Model):
            @appmodels.permalink
            def get_absolute_url(self):
                return ('myapp.urls', 'model_detail', (), {'slug': self.slug})
    """
    def inner(*args, **kwargs):
        return articles_app_reverse(*func(*args, **kwargs))
    return wraps(func)(inner)

############################


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

    @articles_permalink
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
