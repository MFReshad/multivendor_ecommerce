from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    # Cart URLs
    path('', views.CartView.as_view(), name='cart-detail'),
    path('items/', views.CartItemListView.as_view(), name='cart-items'),
    path('add/', views.CartItemCreateView.as_view(), name='add-to-cart'),
    path('add-product/', views.add_to_cart, name='add-product-to-cart'),
    path('items/<int:pk>/', views.CartItemUpdateView.as_view(), name='update-cart-item'),
    path('items/<int:pk>/delete/', views.CartItemDeleteView.as_view(), name='delete-cart-item'),
    path('items/<int:item_id>/quantity/', views.update_cart_item_quantity, name='update-quantity'),
    path('clear/', views.clear_cart, name='clear-cart'),
    path('summary/', views.cart_summary, name='cart-summary'),
    
    # Wishlist URLs
    path('wishlist/', views.WishlistView.as_view(), name='wishlist'),
    path('wishlist/add/', views.add_to_wishlist, name='add-to-wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove-from-wishlist'),
    path('wishlist/move-to-cart/<int:product_id>/', views.move_to_cart, name='move-to-cart'),
]