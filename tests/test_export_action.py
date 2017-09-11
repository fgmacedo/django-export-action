# -- encoding: UTF-8 --

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.http import urlencode

import pytest
from mixer.backend.django import mixer

from export_action import report

from .models import Publication, Reporter, Article, ArticleTag, Tag


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
def test_export_with_related_of_indirect_field_get_should_return_200(admin_client):
    reporter = mixer.blend(Reporter)
    mixer.cycle(3).blend(Article, reporter=reporter)

    params = {
        'related': True,
        'model_ct': ContentType.objects.get_for_model(Article).pk,
        'field': 'articletag',
        'path': 'articletag.id',
    }
    url = "{}?{}".format(reverse('export_action:export'), urlencode(params))
    response = admin_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_AdminExport_with_unregistered_model_should_raise_ValueError(admin_client):
    article = mixer.blend(Article)

    mixer.cycle(3).blend(ArticleTag, article=article)

    params = {
        'ct': ContentType.objects.get_for_model(ArticleTag).pk,
        'ids': ','.join(repr(pk) for pk in ArticleTag.objects.values_list('pk', flat=True))
    }
    url = "{}?{}".format(reverse('export_action:export'), urlencode(params))

    with pytest.raises(ValueError):
        admin_client.get(url)


@pytest.mark.django_db
def test_admin_action_should_redirect_to_export_view(admin_client):
    objects = mixer.cycle(3).blend(Publication)

    ids = [repr(obj.pk) for obj in objects]
    data = {
        "action": "export_selected_objects",
        "_selected_action": ids,
    }
    url = reverse('admin:tests_publication_changelist')
    response = admin_client.post(url, data=data)

    expected_url = "{}?ct={ct}&ids={ids}".format(
        reverse('export_action:export'),
        ct=ContentType.objects.get_for_model(Publication).pk,
        ids=','.join(ids)
    )
    assert response.status_code == 302
    assert response.url.endswith(expected_url)


@pytest.mark.django_db
def test_admin_action_should_redirect_to_export_view_without_ids_for_large_queries(admin_client):
    objects = mixer.cycle(1001).blend(Publication)

    ids = [obj.pk for obj in objects[:50]]
    data = {
        "action": "export_selected_objects",
        "_selected_action": ids,
        "select_across": ids,
    }
    url = reverse('admin:tests_publication_changelist')
    response = admin_client.post(url, data=data)

    assert response.status_code == 302
    assert 'session_key' in response.url

    session_key = response.url[response.url.index('session_key=') + len('session_key='):]
    session_ids = admin_client.session[session_key]
    assert session_ids == [obj.pk for obj in objects]


@pytest.mark.django_db
@pytest.mark.parametrize('output_format', ['html', 'csv', 'xls'])
def test_export_with_related_should_return_200(admin_client, output_format):
    publications = mixer.cycle(5).blend(Publication)
    reporter = mixer.blend(Reporter)
    tag = mixer.blend(Tag, name='python')
    articles = mixer.cycle(3).blend(Article, reporter=reporter, publications=publications)
    for article in articles:
        mixer.blend(ArticleTag, tag=tag, article=article)

    params = {
        'ct': ContentType.objects.get_for_model(Article).pk,
        'ids': ','.join(repr(pk) for pk in Article.objects.values_list('pk', flat=True))
    }
    data = {
        'id': 'on',
        'headline': 'on',
        'reporter__last_name': 'on',
        'reporter__email': 'on',
        'reporter__id': 'on',
        'reporter__first_name': 'on',
        'publications__id': 'on',
        'articletag__id': 'on',
        'publications__title': 'on',
        "__format": output_format,
    }
    url = "{}?{}".format(reverse('export_action:export'), urlencode(params))
    response = admin_client.post(url, data=data)
    assert response.status_code == 200
    assert response.content

    assert Article.objects.first().publications.count() == 5
    assert Article.objects.first().tags.count() == 1
    assert Article.objects.first().reporter == reporter

    url = reverse('admin:tests_publication_changelist')
    response = admin_client.get(url)
    assert response.status_code == 200

    url = reverse('admin:tests_article_changelist')
    response = admin_client.get(url)
    assert response.status_code == 200

    for article in articles:
        url = reverse('admin:tests_article_change', args=[article.pk])
        response = admin_client.get(url)
        assert response.status_code == 200
