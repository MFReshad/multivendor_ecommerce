# apps/products/urls.py

from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Public Product URLs
    path('', views.ProductListView.as_view(), name='product-list'),
    path('<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('search/', views.SearchProductsView.as_view(), name='product-search'),
    path('top-products/', views.TopProductsView.as_view(), name='top-products'),
    
    # Category URLs
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category-detail'),
    
    # Seller Product Management URLs
    path('seller/', views.SellerProductListView.as_view(), name='seller-product-list'),
    path('seller/<int:pk>/', views.SellerProductDetailView.as_view(), name='seller-product-detail'),
    
    # Product Variants URLs
    path('<int:product_id>/variants/', views.ProductVariantView.as_view(), name='product-variants'),
    path('variants/<int:pk>/', views.ProductVariantDetailView.as_view(), name='product-variant-detail'),
    
    # Product Reviews URLs
    path('<int:product_id>/reviews/', views.ProductReviewView.as_view(), name='product-reviews'),
    
    # Statistics URLs
    path('stats/', views.ProductStatsView.as_view(), name='product-stats'),
    
    # Admin URLs
    path('admin/', views.AdminProductListView.as_view(), name='admin-product-list'),
    path('admin/<int:pk>/', views.AdminProductDetailView.as_view(), name='admin-product-detail'),
]