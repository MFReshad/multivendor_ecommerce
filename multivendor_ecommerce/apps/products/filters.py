# apps/products/filters.py
import django_filters
from django.db.models import Avg, Q
from .models import Product, Category


class ProductFilter(django_filters.FilterSet):
    """
    Filter class for product filtering
    """
    # Price range filters
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    
    # Category filter
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        field_name='category'
    )
    
    # Category by ID
    category_id = django_filters.NumberFilter(field_name='category__id')
    
    # Seller filter
    seller = django_filters.NumberFilter(field_name='seller__id')
    seller_name = django_filters.CharFilter(field_name='seller__username', lookup_expr='icontains')
    
    # Stock availability
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    
    # Rating filter
    min_rating = django_filters.NumberFilter(method='filter_min_rating')
    
    # Date filters
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Product name filter
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    
    # Active products only
    is_active = django_filters.BooleanFilter(field_name='is_active')
    
    # Search across multiple fields
    search = django_filters.CharFilter(method='filter_search')
    
    # Order by options
    ordering = django_filters.OrderingFilter(
        fields=(
            ('price', 'price'),
            ('created_at', 'created_at'),
            ('name', 'name'),
            ('stock_quantity', 'stock_quantity'),
        ),
        field_labels={
            'price': 'Price',
            'created_at': 'Date Created',
            'name': 'Product Name',
            'stock_quantity': 'Stock Quantity',
        }
    )

    class Meta:
        model = Product
        fields = {
            'price': ['exact', 'gte', 'lte'],
            'stock_quantity': ['exact', 'gte', 'lte'],
            'is_active': ['exact'],
            'category': ['exact'],
            'seller': ['exact'],
        }

    def filter_in_stock(self, queryset, name, value):
        """
        Filter products based on stock availability
        """
        if value is True:
            return queryset.filter(stock_quantity__gt=0)
        elif value is False:
            return queryset.filter(stock_quantity=0)
        return queryset

    def filter_min_rating(self, queryset, name, value):
        """
        Filter products by minimum average rating
        """
        if value:
            # Annotate with average rating and filter
            return queryset.annotate(
                avg_rating=Avg('reviews__rating')
            ).filter(avg_rating__gte=value)
        return queryset

    def filter_search(self, queryset, name, value):
        """
        Search across multiple fields
        """
        if value:
            return queryset.filter(
                Q(name__icontains=value) |
                Q(description__icontains=value) |
                Q(category__name__icontains=value) |
                Q(seller__username__icontains=value)
            )
        return queryset


class CategoryFilter(django_filters.FilterSet):
    """
    Filter class for category filtering
    """
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    has_products = django_filters.BooleanFilter(method='filter_has_products')

    class Meta:
        model = Category
        fields = ['name']

    def filter_has_products(self, queryset, name, value):
        """
        Filter categories that have active products
        """
        if value is True:
            return queryset.filter(product__is_active=True).distinct()
        elif value is False:
            return queryset.exclude(product__is_active=True).distinct()
        return queryset


class SellerProductFilter(django_filters.FilterSet):
    """
    Filter for seller's own products
    """
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        field_name='category'
    )
    is_active = django_filters.BooleanFilter(field_name='is_active')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    low_stock = django_filters.BooleanFilter(method='filter_low_stock')

    class Meta:
        model = Product
        fields = ['name', 'category', 'is_active', 'price']

    def filter_in_stock(self, queryset, name, value):
        """
        Filter products based on stock availability
        """
        if value is True:
            return queryset.filter(stock_quantity__gt=0)
        elif value is False:
            return queryset.filter(stock_quantity=0)
        return queryset

    def filter_low_stock(self, queryset, name, value):
        """
        Filter products with low stock (less than 10 items)
        """
        if value is True:
            return queryset.filter(stock_quantity__lt=10, stock_quantity__gt=0)
        return queryset


class AdminProductFilter(django_filters.FilterSet):
    """
    Advanced filter for admin product management
    """
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    seller_name = django_filters.CharFilter(
        field_name='seller__username', 
        lookup_expr='icontains'
    )
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        field_name='category'
    )
    is_active = django_filters.BooleanFilter(field_name='is_active')
    seller_approved = django_filters.BooleanFilter(field_name='seller__is_approved')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    has_reviews = django_filters.BooleanFilter(method='filter_has_reviews')
    min_rating = django_filters.NumberFilter(method='filter_min_rating')

    class Meta:
        model = Product
        fields = [
            'name', 'seller_name', 'category', 'is_active', 
            'seller_approved', 'price'
        ]

    def filter_has_reviews(self, queryset, name, value):
        """
        Filter products that have reviews
        """
        if value is True:
            return queryset.filter(reviews__isnull=False).distinct()
        elif value is False:
            return queryset.filter(reviews__isnull=True)
        return queryset

    def filter_min_rating(self, queryset, name, value):
        """
        Filter products by minimum average rating
        """
        if value:
            return queryset.annotate(
                avg_rating=Avg('reviews__rating')
            ).filter(avg_rating__gte=value)
        return queryset