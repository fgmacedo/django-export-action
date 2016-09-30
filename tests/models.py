# -- encoding: UTF-8 --
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Publication(models.Model):
    title = models.CharField(max_length=30)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('title',)


@python_2_unicode_compatible
class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)


@python_2_unicode_compatible
class Tag(models.Model):
    name = models.CharField(max_length=30)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=100)
    publications = models.ManyToManyField(Publication)
    tags = models.ManyToManyField(Tag, through='ArticleTag')
    reporter = models.ForeignKey(Reporter, on_delete=models.CASCADE)

    def __str__(self):
        return self.headline

    class Meta:
        ordering = ('headline',)


@python_2_unicode_compatible
class ArticleTag(models.Model):
    tag = models.ForeignKey(Tag)
    article = models.ForeignKey(Article)

    created_on = models.DateTimeField('created on', auto_now_add=True)

    def __str__(self):
        return "{} on {}".format(self.tag, self.article)

    class Meta:
        ordering = ('created_on',)
