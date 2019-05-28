from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from .admin import production_admin
from . import views

admin.site.site_header = 'FFpasta'

urlpatterns = [
    path('', views.Home.as_view()),
    path('kontakt/', views.ContactView.as_view()),
    path('obnova-hesla/', views.ForgottenPasswordView.as_view()),
    path('zmena-hesla/', views.ChangePasswordView.as_view()),
    path('zmena-hesla/<int:id>/<slug:token>/', views.ChangePasswordView.as_view()),
    path('potvrdit-objednavku/<int:id>/<slug:token>/', views.confirm_order),
    path('odmitnout-objednavku/<int:id>/<slug:token>/', views.reject_order),
    path('prihlaseni/', views.LoginView.as_view()),
    path('objednavky/', views.OrderListView.as_view()),
    path('nova-objednavka/', views.OrderCreateUpdateView.as_view()),
    path('dokonceni-objednavky/', views.OrderFinishView.as_view()),
    path('admin/', admin.site.urls),
    path('produkce/', production_admin.urls),
    path('ajax/<slug:slug>/', views.ProductDetailView.as_view()),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
