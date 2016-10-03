# coding: utf-8

from __future__ import unicode_literals, absolute_import

from itertools import chain

from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import FieldDoesNotExist


def _get_field_by_name(model_class, field_name):
    """
    Compatible with old API of model_class._meta.get_field_by_name(field_name)
    """
    field = model_class._meta.get_field(field_name)
    return (
        field,                                       # field
        field.model,                                 # model
        not field.auto_created or field.concrete,    # direct
        field.many_to_many                           # m2m
    )


def _get_remote_field(field):
    """
    Compatible with Django 1.8~1.10 ('related' was renamed to 'remote_field')
    """
    if hasattr(field, 'remote_field'):
        return field.remote_field
    elif hasattr(field, 'related'):
        return field.related
    else:
        return None


def _get_all_field_names(model):
    """
    100% compatible version of the old API of model._meta.get_all_field_names()
    From: https://docs.djangoproject.com/en/1.9/ref/models/meta/#migrating-from-the-old-api
    """
    return list(set(chain.from_iterable(
        (field.name, field.attname) if hasattr(field, 'attname') else (field.name,)
        for field in model._meta.get_fields()
        # For complete backwards compatibility, you may want to exclude
        # GenericForeignKey from the results.
        if not (field.many_to_one and field.related_model is None)
    )))


def get_relation_fields_from_model(model_class):
    """ Get related fields (m2m, FK, and reverse FK) """
    relation_fields = []
    all_fields_names = _get_all_field_names(model_class)
    for field_name in all_fields_names:
        field, model, direct, m2m = _get_field_by_name(model_class, field_name)
        # get_all_field_names will return the same field
        # both with and without _id. Ignore the duplicate.
        if field_name[-3:] == '_id' and field_name[:-3] in all_fields_names:
            continue
        if m2m or not direct or _get_remote_field(field):
            field.field_name_override = field_name
            relation_fields += [field]
    return relation_fields


def get_direct_fields_from_model(model_class):
    """ Direct, not m2m, not FK """
    direct_fields = []
    all_fields_names = _get_all_field_names(model_class)
    for field_name in all_fields_names:
        field, model, direct, m2m = _get_field_by_name(model_class, field_name)
        if direct and not m2m and not _get_remote_field(field):
            direct_fields += [field]
    return direct_fields


def get_model_from_path_string(root_model, path):
    """ Return a model class for a related model
    root_model is the class of the initial model
    path is like foo__bar where bar is related to foo
    """
    for path_section in path.split('__'):
        if path_section:
            try:
                field, model, direct, m2m = _get_field_by_name(root_model, path_section)
            except FieldDoesNotExist:
                return root_model
            if direct:
                if _get_remote_field(field):
                    try:
                        root_model = _get_remote_field(field).parent_model()
                    except AttributeError:
                        root_model = _get_remote_field(field).model
            else:
                if hasattr(field, 'related_model'):
                    root_model = field.related_model
                else:
                    root_model = field.model
    return root_model


def get_fields(model_class, field_name='', path=''):
    """ Get fields and meta data from a model

    :param model_class: A django model class
    :param field_name: The field name to get sub fields from
    :param path: path of our field in format
        field_name__second_field_name__ect__
    :returns: Returns fields and meta data about such fields
        fields: Django model fields
        properties: Any properties the model has
        path: Our new path
    :rtype: dict
    """
    fields = get_direct_fields_from_model(model_class)
    app_label = model_class._meta.app_label

    if field_name != '':
        field, model, direct, m2m = _get_field_by_name(model_class, field_name)

        path += field_name
        path += '__'
        if direct:  # Direct field
            try:
                new_model = _get_remote_field(field).parent_model
            except AttributeError:
                new_model = _get_remote_field(field).model
        else:  # Indirect related field
            new_model = field.related_model

        fields = get_direct_fields_from_model(new_model)

        app_label = new_model._meta.app_label

    return {
        'fields': fields,
        'path': path,
        'app_label': app_label,
    }


def get_related_fields(model_class, field_name, path=""):
    """ Get fields for a given model """
    if field_name:
        field, model, direct, m2m = _get_field_by_name(model_class, field_name)
        if direct:
            # Direct field
            try:
                new_model = _get_remote_field(field).parent_model()
            except AttributeError:
                new_model = _get_remote_field(field).model
        else:
            # Indirect related field
            if hasattr(field, 'related_model'):  # Django>=1.8
                new_model = field.related_model
            else:
                new_model = field.model()

        path += field_name
        path += '__'
    else:
        new_model = model_class

    new_fields = get_relation_fields_from_model(new_model)
    model_ct = ContentType.objects.get_for_model(new_model)

    return (new_fields, model_ct, path)
