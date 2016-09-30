import uuid
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse, NoReverseMatch
from django.http import HttpResponseRedirect


def export_simple_selected_objects(modeladmin, request, queryset):
    selected = list(queryset.values_list('id', flat=True))
    ct = ContentType.objects.get_for_model(queryset.model)

    try:
        url = reverse("export_action:export")
    except NoReverseMatch:  # Old configuration, maybe? Fall back to old URL scheme.
        url = "/export_action/export_to_xls/"

    if len(selected) > 1000:
        session_key = "export_action_%s" % uuid.uuid4()
        request.session[session_key] = selected
        return HttpResponseRedirect("%s?ct=%s&session_key=%s" % (url, ct.pk, session_key))
    else:
        return HttpResponseRedirect(
            "%s?ct=%s&ids=%s" % (url, ct.pk, ",".join(str(pk) for pk in selected)))

export_simple_selected_objects.short_description = "Export selected items..."

admin.site.add_action(export_simple_selected_objects)
