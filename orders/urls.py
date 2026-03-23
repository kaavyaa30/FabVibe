from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('order-summary/', views.order_summary, name='order_summary'),
    path('payment-method/', views.payment_method_selection, name='payment_method_selection'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('order-history/', views.order_history, name='order_history'),
    path('order-detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('track-order/<int:order_id>/', views.track_order, name='track_order'),
    path('request-return/<int:order_id>/', views.request_return, name='request_return'),
    path('request-exchange/<int:order_id>/', views.request_exchange, name='request_exchange'),
    path('download-invoice/<int:order_id>/', views.download_invoice, name='download_invoice'),
    path('confirm-delivery/<int:order_id>/', views.confirm_delivery, name='confirm_delivery'),
    path('cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('send-otp/<int:order_id>/', views.send_delivery_otp_view, name='send_delivery_otp'),
    path('deliver/', views.deliver_order, name='deliver_order'),
]
