from django.urls import path
from . import views

app_name = 'wallet'

urlpatterns = [
    path('', views.wallet_dashboard, name='dashboard'),
    path('balance/', views.wallet_balance_api, name='balance_api'),
    path('apply/', views.apply_wallet_api, name='apply_api'),
]
