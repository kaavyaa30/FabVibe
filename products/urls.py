from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.home, name='home'),
    path('category/<slug:category_slug>/', views.category_products, name='category_products'),
    path('product/<slug:product_slug>/', views.product_detail, name='product_detail'),
    path('search/', views.search_products, name='search'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/items/', views.get_wishlist_items, name='get_wishlist_items'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('remove-background/', views.remove_background, name='remove_background'),
    path('product/<int:product_id>/reviews/', views.get_product_reviews, name='get_product_reviews'),
    path('product/<int:product_id>/review/submit/', views.submit_review, name='submit_review'),
]
