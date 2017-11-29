=============================
Django Export Action
=============================

.. image:: https://badge.fury.io/py/django-export-action.svg
    :target: https://badge.fury.io/py/django-export-action

.. image:: https://travis-ci.org/fgmacedo/django-export-action.svg?branch=master
    :target: https://travis-ci.org/fgmacedo/django-export-action

.. image:: https://img.shields.io/codecov/c/github/fgmacedo/django-export-action/master.svg?label=branch%20coverage
   :target: https://codecov.io/github/fgmacedo/django-export-action


Generic export action for Django's Admin

Quickstart
----------

Install Django Export Action::

    pip install django-export-action

Include it on INSTALLED_APPS::

    'export_action',

Add to urls:

.. code-block:: python

    url(r'^export_action/', include("export_action.urls", namespace="export_action")),

Usage
-----

Go to any admin page, select fields, then select the export to xls action. Then
check off any fields you want to export.

Features
--------

* Generic action to enable export data from Admin.
* Automatic traversal of model relations.
* Selection of fields to export.
* Can export to XSLx, CSV and HTML.

Running Tests
--------------

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install -r requirements_test.txt
    (myenv) $ py.test


Security
--------

This project assumes staff users are trusted. There may be ways for users to
manipulate this project to get more data access than they should have.
