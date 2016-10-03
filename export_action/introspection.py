# coding: utf-8

from __future__ import unicode_literals, absolute_import

from itertools import chain
import inspect

from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import FieldDoesNotExist


def _get_field_by_name(model_class, field_name):
    """
    Compatible with old API of model_class._meta.get_field_by_name(field_name)
    """
    field = model_class._meta.get_field(field_name)
    return (
        field,
        field.model,
        not field.auto_created or field.concrete,
        field.many_to_many
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
        field = _get_field_by_name(model_class, field_name)
        # get_all_field_names will return the same field
        # both with and without _id. Ignore the duplicate.
        if field_name[-3:] == '_id' and field_name[:-3] in all_fields_names:
            continue
        if field[3] or not field[2] or _get_remote_field(field[0]):
            field[0].field_name = field_name
            relation_fields += [field[0]]
    return relation_fields


def get_direct_fields_from_model(model_class):
    """ Direct, not m2m, not FK """
    direct_fields = []
    all_fields_names = _get_all_field_names(model_class)
    for field_name in all_fields_names:
        field = _get_field_by_name(model_class, field_name)
        if field[2] and not field[3] and not _get_remote_field(field[0]):
            direct_fields += [field[0]]
    return direct_fields


def isprop(v):
    return isinstance(v, property)


def get_properties_from_model(model_class):
    """ Show properties from a model """
    properties = []
    attr_names = [name for (name, value) in inspect.getmembers(model_class, isprop)]
    for attr_name in attr_names:
        if attr_name.endswith('pk'):
            attr_names.remove(attr_name)
        else:
            properties.append(dict(label=attr_name, name=attr_name.strip('_').replace('_', ' ')))
    return sorted(properties, key=lambda k: k['label'])


def get_model_from_path_string(root_model, path):
    """ Return a model class for a related model
    root_model is the class of the initial model
    path is like foo__bar where bar is related to foo
    """
    for path_section in path.split('__'):
        if path_section:
            try:
                field = _get_field_by_name(root_model, path_section)
            except FieldDoesNotExist:
                return root_model
            if field[2]:
                if _get_remote_field(field[0]):
                    try:
                        root_model = _get_remote_field(field[0]).parent_model()
                    except AttributeError:
                        root_model = _get_remote_field(field[0]).model
            else:
                if hasattr(field[0], 'related_model'):
                    root_model = field[0].related_model
                else:
                    root_model = field[0].model
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
    properties = get_properties_from_model(model_class)
    app_label = model_class._meta.app_label

    if field_name != '':
        field = _get_field_by_name(model_class, field_name)

        path += field_name
        path += '__'
        if field[2]:  # Direct field
            try:
                new_model = _get_remote_field(field[0]).parent_model
            except AttributeError:
                new_model = _get_remote_field(field[0]).model
        else:  # Indirect related field
            try:
                new_model = field[0].related_model
            except AttributeError:  # Django 1.7
                new_model = field[0].model

        fields = get_direct_fields_from_model(new_model)

        properties = get_properties_from_model(new_model)
        app_label = new_model._meta.app_label

    return {
        'fields': fields,
        'properties': properties,
        'path': path,
        'app_label': app_label,
    }


def get_related_fields(model_class, field_name, path=""):
    """ Get fields for a given model """
    if field_name:
        field = _get_field_by_name(model_class, field_name)
        if field[2]:
            # Direct field
            try:
                new_model = _get_remote_field(field[0]).parent_model()
            except AttributeError:
                new_model = _get_remote_field(field[0]).model
        else:
            # Indirect related field
            if hasattr(field[0], 'related_model'):  # Django>=1.8
                new_model = field[0].related_model
            else:
                new_model = field[0].model()

        path += field_name
        path += '__'
    else:
        new_model = model_class

    new_fields = get_relation_fields_from_model(new_model)
    model_ct = ContentType.objects.get_for_model(new_model)

    return (new_fields, model_ct, path)
