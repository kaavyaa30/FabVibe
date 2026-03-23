from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login', RedirectView.as_view(url='/users/login/', permanent=False)),
    path('login/', RedirectView.as_view(url='/users/login/', permanent=False)),
    path('register', RedirectView.as_view(url='/users/register/', permanent=False)),
    path('register/', RedirectView.as_view(url='/users/register/', permanent=False)),
    path('', include('products.urls')),
    path('users/', include('users.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('admin-panel/', include('admin_panel.urls')),
    path('wallet/', include('wallet.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
