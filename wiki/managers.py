from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.db.models import Q
from django.db.models.query import QuerySet, EmptyQuerySet
from django import VERSION as DJANGO_VERSION

from mptt.managers import TreeManager


class QuerySetCompatMixin(object):

    def get_queryset_compat(self):
        get_queryset = (self.get_queryset
                        if hasattr(self, 'get_queryset')
                        else self.get_query_set)
        return get_queryset()


class ArticleQuerySet(QuerySet):

    def can_read(self, user):
        """Filter objects so only the ones with a user's reading access
        are included"""
        if user.has_perm('wiki.moderator'):
            return self
        if user.is_anonymous():
            q = self.filter(other_read=True)
        else:
            q = self.filter(Q(other_read=True) |
                            Q(owner=user) |
                            (Q(group__user=user) & Q(group_read=True))
                            )
        return q

    def can_write(self, user):
        """Filter objects so only the ones with a user's writing access
        are included"""
        if user.has_perm('wiki.moderator'):
            return self
        if user.is_anonymous():
            q = self.filter(other_write=True)
        else:
            q = self.filter(Q(other_write=True) |
                            Q(owner=user) |
                            (Q(group__user=user) & Q(group_write=True))
                            )
        return q

    def active(self):
        return self.filter(current_revision__deleted=False)


class ArticleEmptyQuerySet(EmptyQuerySet):

    def can_read(self, user):
        return self

    def can_write(self, user):
        return self

    def active(self):
        return self


class ArticleFkQuerySetMixin():

    def can_read(self, user):
        """Filter objects so only the ones with a user's reading access
        are included"""
        if user.has_perm('wiki.moderate'):
            return self
        if user.is_anonymous():
            q = self.filter(article__other_read=True)
        else:
            # https://github.com/benjaoming/django-wiki/issues/67
            q = self.filter(
                Q(article__other_read=True) | Q(article__owner=user) |
                (Q(article__group__user=user) & Q(
                    article__group_read=True))).distinct()
        return q

    def can_write(self, user):
        """Filter objects so only the ones with a user's writing access
        are included"""
        if user.has_perm('wiki.moderate'):
            return self
        if user.is_anonymous():
            q = self.filter(article__other_write=True)
        else:
            # https://github.com/benjaoming/django-wiki/issues/67
            q = self.filter(
                Q(article__other_write=True) | Q(article__owner=user) |
                (Q(article__group__user=user) & Q(
                    article__group_write=True))).distinct()
        return q

    def active(self):
        return self.filter(article__current_revision__deleted=False)


class ArticleFkEmptyQuerySetMixin():

    def can_read(self, user):
        return self

    def can_write(self, user):
        return self

    def active(self):
        return self


class ArticleFkQuerySet(ArticleFkQuerySetMixin, QuerySet):
    pass


class ArticleFkEmptyQuerySet(ArticleFkEmptyQuerySetMixin, EmptyQuerySet):
    pass


class ArticleManager(QuerySetCompatMixin, models.Manager):

    def get_empty_query_set(self):
        # Pre 1.6 django, we needed a custom inheritor of EmptyQuerySet
        # to pass custom methods. However, 1.6 introduced that EmptyQuerySet
        # cannot be instantiated but instead passes through the methods
        # of the custom QuerySet.
        # See: https://code.djangoproject.com/ticket/22817
        if DJANGO_VERSION < (1, 6):
            return ArticleEmptyQuerySet(self.model, using=self._db)
        return self.get_queryset_compat().none()

    def get_queryset(self):
        return ArticleQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset_compat().active()

    def can_read(self, user):
        return self.get_queryset_compat().can_read(user)

    def can_write(self, user):
        return self.get_queryset_compat().can_write(user)

    get_query_set = get_queryset  # Django 1.5 compat


class ArticleFkManager(QuerySetCompatMixin, models.Manager):

    def get_empty_query_set(self):
        # Pre 1.6 django, we needed a custom inheritor of EmptyQuerySet
        # to pass custom methods. However, 1.6 introduced that EmptyQuerySet
        # cannot be instantiated but instead passes through the methods
        # of the custom QuerySet.
        # See: https://code.djangoproject.com/ticket/22817
        if DJANGO_VERSION < (1, 6):
            return ArticleFkEmptyQuerySet(model=self.model)
        return self.get_queryset_compat().none()

    def get_queryset(self):
        return ArticleFkQuerySet(self.model, using=self._db)

    get_query_set = get_queryset  # Django 1.5 compat

    def active(self):
        return self.get_queryset_compat().active()

    def can_read(self, user):
        return self.get_queryset_compat().can_read(user)

    def can_write(self, user):
        return self.get_queryset_compat().can_write(user)


class URLPathEmptyQuerySet(EmptyQuerySet, ArticleFkEmptyQuerySetMixin):

    def select_related_common(self):
        return self

    def default_order(self):
        return self

class URLPathQuerySet(QuerySet, ArticleFkQuerySetMixin):

    def select_related_common(self):
        return self.select_related(
            "parent",
            "article__current_revision",
            "article__owner")
    
    def default_order(self):
        """Returns elements by there article order"""
        return self.order_by('article__current_revision__title')


class URLPathManager(QuerySetCompatMixin, TreeManager):
    
    def get_empty_query_set(self):
        # Pre 1.6 django, we needed a custom inheritor of EmptyQuerySet
        # to pass custom methods. However, 1.6 introduced that EmptyQuerySet
        # cannot be instantiated but instead passes through the methods
        # of the custom QuerySet.
        # See: https://code.djangoproject.com/ticket/22817
        if DJANGO_VERSION < (1, 6):
            return URLPathEmptyQuerySet(model=self.model)
        return self.get_queryset_compat().none()

    def get_queryset(self):
        """Return a QuerySet with the same ordering as the TreeManager."""
        return URLPathQuerySet(self.model, using=self._db).order_by(
            self.tree_id_attr, self.left_attr)

    get_query_set = get_queryset  # Django 1.5 compat

    def select_related_common(self):
        return self.get_queryset_compat().common_select_related()

    def active(self):
        return self.get_queryset_compat().active()

    def can_read(self, user):
        return self.get_queryset_compat().can_read(user)

    def can_write(self, user):
        return self.get_queryset_compat().can_write(user)
