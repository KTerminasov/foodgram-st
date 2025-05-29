from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from api.views import get_recipe_by_short_link

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('short/<slug:short_link>/', get_recipe_by_short_link)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
