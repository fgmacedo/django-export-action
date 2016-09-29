# -- encoding: UTF-8 --
from django.db import models


class ModelUnderTest(models.Model):
    value = models.IntegerField(unique=True)


class ModelWithRelated(models.Model):
    mut = models.ForeignKey(ModelUnderTest)
    value = models.IntegerField(unique=True)
