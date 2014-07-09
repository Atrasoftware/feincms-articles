from django import template

from articles.models import Article
from articles.modules.category.models import Category
from articles.utils import parse_tokens
from django.utils.translation import get_language

register = template.Library()

class CategoriesNode(template.Node):
    """
        Output a list of categories.

        Usage:
            {% categories %}
    """
    def __init__(self, selected=None, current=None):
        self.selected = selected
        self.current = current

    def render(self, context):
        selected = self.selected and self.selected.resolve(context)
        current = self.current and self.current.resolve(context)

        user = 'request' in context and context['request'].user or None
        categories = None
        if current is None:
            categories = Category.objects.active(user=user).filter(parent__isnull=True)
        else:
            if selected is not None:
                # is the selected category a descendant of
                if current.get_descendants(include_self=True).filter(pk=selected.pk).count() > 0:
                    categories = current.children.filter(Category.objects.active_query(user=user))

        if categories is not None:
            categories = categories.distinct()

        t = template.loader.select_template(['articles/categories.html'])
        context.push()
        context['selected'] = selected
        context['categories'] = categories
        output = t.render(context)
        context.pop()

        return output


@register.tag()
def articlecategories(parser, token):
    bits = token.split_contents()

    args, kwargs = parse_tokens(parser, bits)

    return CategoriesNode(*args, **kwargs)


class FilteredArticlesNode(template.Node):
    """
        Output a list of articles, filtered by category & current
        language. If as varname is specified then add the result to 
        the context.

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
                filter(language__exact=get_language()).\
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
