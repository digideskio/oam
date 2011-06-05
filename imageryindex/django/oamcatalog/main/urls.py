from django.conf.urls.defaults import *

urlpatterns = patterns('main.views',
    # Example:
    (r'^$', 'home'),
    (r'^image/(?P<id>[0-9]+)/$', 'image_browse'),
    (r'^layer/(?P<id>[0-9]+)/', 'layer_browse'),
    (r'^layer/new/$', 'layer_create'),
    (r'^layer/$', 'layer_list'),
    (r'^image/(?P<id>[0-9]+)/(?P<size>thumbnail|preview|large).jpg$', 'image_preview'),
    (r'^license/(?P<id>[0-9]+)/$', 'license_browse'),
    (r'^api/layer/$', 'layer'),
    (r'^api/layer/(?P<id>[0-9]+)/$', 'layer'),
    (r'^api/license/$', 'license'),
    (r'^api/license/(?P<id>[0-9]+)/$', 'license'),
    (r'^api/image/$', 'image'),
    (r'^api/image/(?P<id>[0-9]+)/$', 'image'),
    (r'^api/image/(?P<image>[0-9]+)/layer/(?P<layer>[0-9]+)/$', 'image_layer'),
    (r'^api/mirror/$', 'mirror'),
    (r'^api/mirror/(?P<id>[0-9]+)/$', 'mirror'),
)
