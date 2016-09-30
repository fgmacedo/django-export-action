# -- encoding: UTF-8 --
import random

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.http import urlencode

import pytest
from mixer.backend.django import mixer

from export_action import report

from .models import Publication, Reporter, Article


@pytest.mark.django_db
@pytest.mark.parametrize('output_name', ['html', 'csv'])
def test_AdminExport_list_to_method_response_should_return_200(admin_user, output_name):
    mixer.cycle(3).blend(Publication)
    data = report.report_to_list(Publication.objects.all(), ['title'], admin_user)

    method = getattr(report, 'list_to_{}_response'.format(output_name))
    res = method(data)
    assert res.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize('output_format', ['html', 'csv', 'xls'])
def test_AdminExport_post_should_return_200(admin_client, output_format):
    mixer.cycle(3).blend(Publication)

    params = {
        'ct': ContentType.objects.get_for_model(Publication).pk,
        'ids': ','.join(repr(pk) for pk in Publication.objects.values_list('pk', flat=True))
    }
    data = {
        "title": "on",
        "__format": output_format,
    }
    url = "{}?{}".format(reverse('export_action:export'), urlencode(params))
    response = admin_client.post(url, data=data)
    assert response.status_code == 200


@pytest.mark.django_db
def test_AdminExport_get_should_return_200(admin_client):
    mixer.cycle(3).blend(Publication)

    params = {
        'ct': ContentType.objects.get_for_model(Publication).pk,
        'ids': ','.join(repr(pk) for pk in Publication.objects.values_list('pk', flat=True))
    }
    url = "{}?{}".format(reverse('export_action:export'), urlencode(params))
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_AdminExport_with_related_get_should_return_200(admin_client):
    reporter = mixer.blend(Reporter)
    mixer.cycle(3).blend(Article, reporter=reporter)

    params = {
        'related': True,
        'model_ct': ContentType.objects.get_for_model(Article).pk,
        'field': 'reporter',
        'path': 'reporter.first_name',
    }
    url = "{}?{}".format(reverse('export_action:export'), urlencode(params))
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_AdminExport_with_unregistered_model_should_raise_ValueError(admin_client):
    reporter = mixer.blend(Reporter)
    mixer.cycle(3).blend(Article, reporter=reporter)

    params = {
        'ct': ContentType.objects.get_for_model(Article).pk,
        'ids': ','.join(repr(pk) for pk in Article.objects.values_list('pk', flat=True))
    }
    url = "{}?{}".format(reverse('export_action:export'), urlencode(params))

    with pytest.raises(ValueError):
        admin_client.get(url)
