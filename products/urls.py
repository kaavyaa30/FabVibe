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
    path('product/<int:product_id>/reviews/', views.get_product_reviews, name='get_product_reviews'),
    path('product/<int:product_id>/review/submit/', views.submit_review, name='submit_review'),
    # New features
    path('size-recommender/', views.size_recommender, name='size_recommender'),
    path('product/<int:product_id>/complete-the-look/', views.complete_the_look, name='complete_the_look'),
    path('product/<int:product_id>/track-view/', views.track_recently_viewed, name='track_recently_viewed'),
    path('recently-viewed/', views.get_recently_viewed, name='recently_viewed'),
    path('product/<int:product_id>/stock-alert/', views.subscribe_stock_alert, name='stock_alert'),
    # Virtual Try-On
    path('tryon/', views.photo_tryon_page, name='photo_tryon'),
    path('tryon/enqueue/', views.photo_tryon_enqueue, name='photo_tryon_enqueue'),
    path('tryon/status/<str:task_id>/', views.photo_tryon_status, name='photo_tryon_status'),
    path('tryon/history/', views.tryon_history, name='tryon_history'),
    path('product/<int:product_id>/sizes/', views.get_product_sizes, name='get_product_sizes'),
    # AR Try-On (MediaPipe — client-side only)
    path('product/<int:product_id>/ar-tryon/', views.ar_tryon, name='ar_tryon'),
]
