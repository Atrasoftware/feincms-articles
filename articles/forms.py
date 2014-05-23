#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: dzaltron
# @Date:   2014-05-20 13:28:56
# @Last Modified by:   dzaltron
# @Last Modified time: 2014-05-20 13:33:11

from __future__ import absolute_import, unicode_literals

from mptt.forms import MPTTAdminForm


class ArticleAdminForm(MPTTAdminForm):
    never_copy_fields = (
        'title', 'slug', 'parent', 'active', 'override_url',
        'translation_of', '_content_title', '_page_title')