Developer Notes
===============

This document includes some notes targeted towards OAM developers.

OpenLayers Build
++++++++++++++++

OAM uses a slimmed down OL build; for development purposes, you should 
generally use a 'full' build, then build a new OL starting with the build
profile in the django/util directory.

LDAP Auth
+++++++++

By default, OAM uses LDAP auth. You can disable this by commenting out 

       'django_auth_ldap.backend.LDAPBackend',

in AUTHENTICATION_BACKENDS in the settings.py.
