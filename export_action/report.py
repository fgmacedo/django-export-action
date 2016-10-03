# coding: utf-8

from __future__ import unicode_literals, absolute_import

from collections import namedtuple
from itertools import chain
import csv
import re
try:
    from decimal import Decimal
except:
    from Decimal import Decimal

from django.http import HttpResponse
from django.utils.text import force_text
from django.template.loader import render_to_string
from django.utils import timezone

from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook
from openpyxl.writer.excel import save_virtual_workbook

from six import BytesIO, text_type

from .introspection import get_model_from_path_string


DisplayField = namedtuple(
    "DisplayField",
    "path field field_verbose aggregate total group choices field_type",
)


def generate_filename(title, ends_with):
    title = title.split('.')[0]
    title.replace(' ', '_')
    title += ('_' + timezone.now().strftime("%Y-%m-%d_%H%M"))
    if not title.endswith(ends_with):
        title += ends_with
    return title


def _can_change_or_view(model, user):
    """ Return True iff `user` has either change or view permission
    for `model`.
    """
    try:
        model_name = model._meta.model_name
    except AttributeError:
        # Needed for Django 1.4.* (LTS).
        model_name = model._meta.module_name

    app_label = model._meta.app_label
    can_change = user.has_perm(app_label + '.change_' + model_name)
    can_view = user.has_perm(app_label + '.view_' + model_name)

    return can_change or can_view


def report_to_list(queryset, display_fields, user, preview=False):
    """ Create list from a report with all data filtering.

    queryset: initial queryset to generate results
    display_fields: list of field references or DisplayField models
    user: requesting user
    preview: return only first 50 rows

    Returns list, message in case of issues.
    """
    model_class = queryset.model
    objects = queryset

    if not _can_change_or_view(model_class, user):
        return [], 'Permission Denied'

    if isinstance(display_fields, list):
        # Convert list of strings to DisplayField objects.

        new_display_fields = []

        for display_field in display_fields:
            field_list = display_field.split('__')
            field = field_list[-1]
            path = '__'.join(field_list[:-1])

            if path:
                path += '__'  # Legacy format to append a __ here.

            new_model = get_model_from_path_string(model_class, path)
            model_field = new_model._meta.get_field(field)
            choices = model_field.choices
            df = DisplayField(
                path,
                field,
                '',
                '',
                None,
                None,
                choices,
                ''
            )
            new_display_fields.append(df)

        display_fields = new_display_fields

    message = ""

    # Display Values

    display_field_paths = []

    for i, display_field in enumerate(display_fields):
        model = get_model_from_path_string(model_class, display_field.path)

        if display_field.field_type == "Invalid":
            continue

        if not model or _can_change_or_view(model, user):
            display_field_key = display_field.path + display_field.field

            display_field_paths.append(display_field_key)

        else:
            message += 'Error: Permission denied on access to {0}.'.format(
                display_field.name
            )

    # Select pk for primary and m2m relations in order to retrieve objects
    # for adding properties to report rows. Group-by queries do not support
    # Property nor Custom Field filters.

    display_field_paths.insert(0, 'pk')

    filtered_report_rows = []
    values_and_properties_list = []

    values_list = objects.values_list(*display_field_paths)

    for row in values_list:
        row = list(row)
        values_and_properties_list.append(row[1:])

        filtered_report_rows.append(values_and_properties_list[-1])

        if preview and len(filtered_report_rows) == 50:
            break

    # Sort results if requested.
    values_and_properties_list = filtered_report_rows

    # Build mapping from display field position to choices list.

    choice_lists = {}
    for df in display_fields:
        if df.choices and hasattr(df, 'choices_dict'):
            df_choices = df.choices_dict
            # Insert blank and None as valid choices.
            df_choices[''] = ''
            df_choices[None] = ''
            choice_lists[df.position] = df_choices

    # Build mapping from display field position to format.

    display_formats = {}

    for df in display_fields:
        if hasattr(df, 'display_format') and df.display_format:
            display_formats[df.position] = df.display_format

    def formatter(value, style):
        # Convert value to Decimal to apply numeric formats.
        try:
            value = Decimal(value)
        except Exception:
            pass

        try:
            return style.string.format(value)
        except ValueError:
            return value

    # Iterate rows and convert values by choice lists and field formats.

    final_list = []

    for row in values_and_properties_list:
        row = list(row)

        for position, choice_list in choice_lists.items():
            try:
                row[position] = text_type(choice_list[row[position]])
            except Exception:
                row[position] = text_type(row[position])

        for pos, style in display_formats.items():
            row[pos] = formatter(row[pos], style)

        final_list.append(row)

    values_and_properties_list = final_list

    return values_and_properties_list, message


def build_sheet(data, ws, sheet_name='report', header=None, widths=None):
    first_row = 1
    column_base = 1

    ws.title = re.sub(r'\W+', '', sheet_name)[:30]
    if header:
        for i, header_cell in enumerate(header):
            cell = ws.cell(row=first_row, column=i+column_base)
            cell.value = header_cell
            cell.font = Font(bold=True)
            if widths:
                ws.column_dimensions[get_column_letter(i+1)].width = widths[i]

    for row in data:
        for i in range(len(row)):
            item = row[i]
            # If item is a regular string
            if isinstance(item, str):
                # Change it to a unicode string
                try:
                    row[i] = text_type(item)
                except UnicodeDecodeError:
                    row[i] = text_type(item.decode('utf-8', 'ignore'))
            elif type(item) is dict:
                row[i] = text_type(item)
        try:
            ws.append(row)
        except ValueError as e:
            ws.append([e.message])
        except:
            ws.append(['Unknown Error'])


def list_to_workbook(data, title='report', header=None, widths=None):
    """ Create just a openpxl workbook from a list of data """
    wb = Workbook()
    title = re.sub(r'\W+', '', title)[:30]

    if isinstance(data, dict):
        i = 0
        for sheet_name, sheet_data in data.items():
            if i > 0:
                wb.create_sheet()
            ws = wb.worksheets[i]
            build_sheet(
                sheet_data, ws, sheet_name=sheet_name, header=header)
            i += 1
    else:
        ws = wb.worksheets[0]
        build_sheet(data, ws, header=header, widths=widths)
    return wb


def build_xlsx_response(wb, title="report"):
    """ Take a workbook and return a xlsx file response """
    title = generate_filename(title, '.xlsx')
    myfile = BytesIO()
    myfile.write(save_virtual_workbook(wb))
    response = HttpResponse(
        myfile.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=%s' % title
    response['Content-Length'] = myfile.tell()
    return response


def list_to_xlsx_response(data, title='report', header=None,
                          widths=None):
    """ Make 2D list into a xlsx response for download
    data can be a 2d array or a dict of 2d arrays
    like {'sheet_1': [['A1', 'B1']]}
    """
    wb = list_to_workbook(data, title, header, widths)
    return build_xlsx_response(wb, title=title)


def list_to_csv_response(data, title='report', header=None, widths=None):
    """ Make 2D list into a csv response for download data.
    """
    response = HttpResponse(content_type="text/csv; charset=UTF-8")
    cw = csv.writer(response)
    for row in chain([header] if header else [], data):
        cw.writerow([force_text(s).encode(response.charset) for s in row])
    return response


def list_to_html_response(data, title='', header=None):
    html = render_to_string('export_action/report_html.html', locals())
    return HttpResponse(html)
