from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Buyer URLs
    path('', views.OrderListCreateView.as_view(), name='order-list-create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('<int:pk>/status/', views.update_order_status, name='update-order-status'),
    path('stats/', views.buyer_order_stats, name='buyer-order-stats'),
    
    # Seller URLs
    path('seller/orders/', views.SellerOrdersView.as_view(), name='seller-orders'),
    path('seller/items/', views.OrderItemListView.as_view(), name='seller-order-items'),
    path('seller/items/<int:pk>/', views.OrderItemUpdateView.as_view(), name='order-item-detail'),
    path('seller/items/<int:pk>/status/', views.update_order_item_status, name='update-order-item-status'),
    path('seller/stats/', views.seller_order_stats, name='seller-order-stats'),
    
    # Admin URLs
    path('admin/orders/', views.AdminOrderListView.as_view(), name='admin-orders'),
]