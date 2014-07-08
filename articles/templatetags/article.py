from django import template

from ..models import Article
from ..utils import parse_tokens

register = template.Library()


class ArticlesNode(template.Node):
    """
        Output a list of articles.
        If as varname is specified then add the result to the context.

        Usage:
            {% articles %}
            OR
            {% articles articles %}
            OR
            {% articles articles limit %}
            OR
            {% articles as artilce_list %}
            OR
            {% articles articles as artilce_list %}
            OR
            {% articles limit=limit as artilce_list %}
    """
    def __init__(self, articles=None, limit=None, varname=None):
        self.articles = articles
        self.limit = limit
        self.varname = varname

    def render(self, context):
        articles = self.articles and self.articles.resolve(context)
        limit = self.limit and self.limit.resolve(context)

        if articles is None:
            articles = Article.objects.active().select_related()

        if limit is not None:
            articles = articles[:limit]

        if self.varname is not None:
            context[self.varname] = articles
            return ''
        else:
            t = template.loader.select_template(['articles/articles.html'])
            context.push()
            context['articles'] = articles
            output = t.render(context)
            context.pop()

            return output


@register.tag()
def articles(parser, token):
    bits = token.split_contents()

    varname = None
    try:
        if bits[-2] == 'as':
            varname = bits[-1]
            bits = bits[:-2]
    except IndexError:
        pass

    args, kwargs = parse_tokens(parser, bits)
    if varname is not None:
        kwargs['varname'] = varname

    return ArticlesNode(*args, **kwargs)


class FilteredArticlesNode(template.Node):
    """
        Output a list of articles.
        If as varname is specified then add the result to the context.

        Usage:
            {% articles %}
            OR
            {% articles articles %}
            OR
            {% articles articles limit %}
            OR
            {% articles as artilce_list %}
            OR
            {% articles articles as artilce_list %}
            OR
            {% articles limit=limit as artilce_list %}
            OR
            {% articles category=categoryslug as filtered_article_list %}
    """
    def __init__(self, category_slug=None, articles=None, limit=None, varname=None):
        self.category_slug = category_slug
        self.articles = articles
        self.limit = limit
        self.varname = varname

    def render(self, context):
        articles = self.articles and self.articles.resolve(context)
        limit = self.limit and self.limit.resolve(context)
        category_slug = self.category_slug and\
            self.category_slug.resolve(context)
        category = Category.objects.get(slug__iexact=category_slug)

        if articles is None:
            articles = Article.objects.active().select_related().\
                filter(category_id__exact=category.id).\
                order_by(category.order_by)

        if limit is not None:
            articles = articles[:limit]

        if self.varname is not None:
            context[self.varname] = articles
            return ''
        else:
            t = template.loader.select_template(['articles/articles.html'])
            context.push()
            context['articles'] = articles
            output = t.render(context)
            context.pop()

            return output


@register.tag()
def articles_with_categoryslug(parser, token):
    bits = token.split_contents()

    varname = None
    try:
        if bits[-2] == 'as':
            varname = bits[-1]
            bits = bits[:-2]
    except IndexError:
        pass

    args, kwargs = parse_tokens(parser, bits)
    if varname is not None:
        kwargs['varname'] = varname

    return FilteredArticlesNode(*args, **kwargs)


from django.core.urlresolvers import NoReverseMatch
from django.template import TemplateSyntaxError

from articles.bases import articles_app_reverse as do_articles_app_reverse
from django.utils.encoding import smart_str
from django.template.defaulttags import kwarg_re


class ArticlesAppReverseNode(template.Node):
    def __init__(self, view_name, urlconf, args, kwargs, asvar):
        self.view_name = view_name
        self.urlconf = urlconf
        self.args = args
        self.kwargs = kwargs
        self.asvar = asvar

    def render(self, context):
        args = [arg.resolve(context) for arg in self.args]
        kwargs = dict([
            (smart_str(k, 'ascii'), v.resolve(context))
            for k, v in self.kwargs.items()])
        view_name = self.view_name.resolve(context)
        urlconf = self.urlconf.resolve(context)

        try:
            url = do_articles_app_reverse(
                view_name, urlconf, args=args, kwargs=kwargs,
                current_app=context.current_app)
        except NoReverseMatch:
            if self.asvar is None:
                raise
            url = ''

        if self.asvar:
            context[self.asvar] = url
            return ''
        else:
            return url


@register.tag
def articles_app_reverse(parser, token):
    bits = token.split_contents()
    if len(bits) < 3:
        raise TemplateSyntaxError(
            "'%s' takes at least two arguments"
            " (path to a view and a urlconf)" % bits[0])
    viewname = parser.compile_filter(bits[1])
    urlconf = parser.compile_filter(bits[2])
    args = []
    kwargs = {}
    asvar = None
    bits = bits[3:]
    if len(bits) >= 2 and bits[-2] == 'as':
        asvar = bits[-1]
        bits = bits[:-2]

    if len(bits):
        for bit in bits:
            match = kwarg_re.match(bit)
            if not match:
                raise TemplateSyntaxError(
                    "Malformed arguments to app_reverse tag")
            name, value = match.groups()
            if name:
                kwargs[name] = parser.compile_filter(value)
            else:
                args.append(parser.compile_filter(value))

    return ArticlesAppReverseNode(viewname, urlconf, args, kwargs, asvar)
