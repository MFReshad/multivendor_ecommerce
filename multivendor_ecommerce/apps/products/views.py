# apps/products/views.py

from rest_framework import status, generics, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count
from django.shortcuts import get_object_or_404
from .models import Product, Category, ProductVariant, ProductReview
from .serializers import (
    ProductSerializer, 
    ProductDetailSerializer,
    CategorySerializer,
    ProductVariantSerializer,
    ProductReviewSerializer,
    ProductCreateUpdateSerializer
)
from .filters import ProductFilter


class ProductListView(generics.ListAPIView):
    """
    Public view to list all products with search and filtering
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'category__name', 'seller__username']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Product.objects.filter(
            is_active=True,
            stock_quantity__gt=0,
            seller__is_approved=True
        ).select_related('seller', 'category').prefetch_related('reviews')
        
        # Add average rating annotation
        queryset = queryset.annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )
        
        return queryset


class ProductDetailView(generics.RetrieveAPIView):
    """
    Public view to get product details with reviews
    """
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'pk'

    def get_queryset(self):
        return Product.objects.filter(
            is_active=True,
            seller__is_approved=True
        ).select_related('seller', 'category').prefetch_related(
            'variants', 'reviews__buyer'
        )


class CategoryListView(generics.ListCreateAPIView):
    """
    List categories (public) and create new categories (admin only)
    """
    serializer_class = CategorySerializer
    queryset = Category.objects.all().order_by('name')

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        if request.user.user_type != 'admin':
            return Response({
                'error': 'Only admins can create categories'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Category management (admin only)
    """
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def update(self, request, *args, **kwargs):
        if request.user.user_type != 'admin':
            return Response({
                'error': 'Only admins can update categories'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.user_type != 'admin':
            return Response({
                'error': 'Only admins can delete categories'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class SellerProductListView(generics.ListCreateAPIView):
    """
    Seller's own products - list and create
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'stock_quantity']
    ordering = ['-created_at']

    def get_queryset(self):
        if self.request.user.user_type == 'seller':
            return Product.objects.filter(
                seller=self.request.user
            ).select_related('category').prefetch_related('reviews')
        return Product.objects.none()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer
        return ProductSerializer

    def perform_create(self, serializer):
        if self.request.user.user_type != 'seller':
            raise permissions.PermissionDenied("Only sellers can create products")
        
        if not self.request.user.is_approved:
            raise permissions.PermissionDenied("Your seller account is not approved")
        
        serializer.save(seller=self.request.user)


class SellerProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Seller's product management - view, update, delete
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer

    def get_queryset(self):
        if self.request.user.user_type == 'seller':
            return Product.objects.filter(
                seller=self.request.user
            ).select_related('category').prefetch_related('variants', 'reviews')
        return Product.objects.none()

    def update(self, request, *args, **kwargs):
        if request.user.user_type != 'seller':
            return Response({
                'error': 'Only sellers can update products'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.user_type != 'seller':
            return Response({
                'error': 'Only sellers can delete products'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class ProductVariantView(APIView):
    """
    Manage product variants (seller only)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, product_id):
        """Get all variants for a product"""
        try:
            product = Product.objects.get(id=product_id)
            
            # Check if user owns the product (seller) or if it's public access
            if request.user.user_type == 'seller' and product.seller != request.user:
                return Response({
                    'error': 'You can only view variants of your own products'
                }, status=status.HTTP_403_FORBIDDEN)
            
            variants = ProductVariant.objects.filter(product=product)
            serializer = ProductVariantSerializer(variants, many=True)
            return Response(serializer.data)
            
        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, product_id):
        """Create new variant for product"""
        if request.user.user_type != 'seller':
            return Response({
                'error': 'Only sellers can create product variants'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            product = Product.objects.get(id=product_id, seller=request.user)
            serializer = ProductVariantSerializer(data=request.data)
            
            if serializer.is_valid():
                serializer.save(product=product)
                return Response({
                    'message': 'Product variant created successfully',
                    'variant': serializer.data
                }, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found or you do not own this product'
            }, status=status.HTTP_404_NOT_FOUND)


class ProductVariantDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage individual product variant
    """
    serializer_class = ProductVariantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.user_type == 'seller':
            return ProductVariant.objects.filter(product__seller=self.request.user)
        return ProductVariant.objects.none()


class ProductReviewView(APIView):
    """
    Product review management
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, product_id):
        """Get all reviews for a product"""
        try:
            product = Product.objects.get(id=product_id)
            reviews = ProductReview.objects.filter(
                product=product
            ).select_related('buyer').order_by('-created_at')
            
            serializer = ProductReviewSerializer(reviews, many=True)
            return Response({
                'reviews': serializer.data,
                'total_reviews': reviews.count(),
                'average_rating': reviews.aggregate(Avg('rating'))['rating__avg'] or 0
            })
            
        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, product_id):
        """Create a new review (buyers only, after purchase)"""
        if request.user.user_type != 'buyer':
            return Response({
                'error': 'Only buyers can leave reviews'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            product = Product.objects.get(id=product_id)
            
            # Check if user has purchased this product
            from apps.orders.models import OrderItem
            has_purchased = OrderItem.objects.filter(
                order__buyer=request.user,
                product=product,
                order__status='delivered'
            ).exists()
            
            if not has_purchased:
                return Response({
                    'error': 'You can only review products you have purchased'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if user already reviewed this product
            existing_review = ProductReview.objects.filter(
                product=product,
                buyer=request.user
            ).exists()
            
            if existing_review:
                return Response({
                    'error': 'You have already reviewed this product'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = ProductReviewSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(product=product, buyer=request.user)
                return Response({
                    'message': 'Review added successfully',
                    'review': serializer.data
                }, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)


class TopProductsView(APIView):
    """
    Get top-selling and highly-rated products
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Get top-rated products
        top_rated = Product.objects.filter(
            is_active=True,
            seller__is_approved=True
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        ).filter(
            review_count__gte=1,
            avg_rating__gte=4.0
        ).order_by('-avg_rating', '-review_count')[:10]

        # Get products with most reviews (popular)
        most_reviewed = Product.objects.filter(
            is_active=True,
            seller__is_approved=True
        ).annotate(
            review_count=Count('reviews')
        ).filter(
            review_count__gte=1
        ).order_by('-review_count')[:10]

        # Get recently added products
        recent_products = Product.objects.filter(
            is_active=True,
            seller__is_approved=True
        ).order_by('-created_at')[:10]

        return Response({
            'top_rated': ProductSerializer(top_rated, many=True).data,
            'most_reviewed': ProductSerializer(most_reviewed, many=True).data,
            'recent_products': ProductSerializer(recent_products, many=True).data
        })


class SearchProductsView(APIView):
    """
    Advanced product search
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.GET.get('q', '')
        category_id = request.GET.get('category')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        min_rating = request.GET.get('min_rating')
        seller_id = request.GET.get('seller')

        products = Product.objects.filter(
            is_active=True,
            seller__is_approved=True
        ).select_related('seller', 'category').prefetch_related('reviews')

        # Apply filters
        if query:
            products = products.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query) |
                Q(seller__username__icontains=query)
            )

        if category_id:
            products = products.filter(category_id=category_id)

        if min_price:
            products = products.filter(price__gte=min_price)

        if max_price:
            products = products.filter(price__lte=max_price)

        if seller_id:
            products = products.filter(seller_id=seller_id)

        # Add rating filter
        if min_rating:
            products = products.annotate(
                avg_rating=Avg('reviews__rating')
            ).filter(avg_rating__gte=min_rating)

        # Add pagination
        page_size = 20
        page = int(request.GET.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size

        total_products = products.count()
        products = products[start:end]

        serializer = ProductSerializer(products, many=True)

        return Response({
            'products': serializer.data,
            'total': total_products,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_products + page_size - 1) // page_size
        })


# Admin Views
class AdminProductListView(generics.ListAPIView):
    """
    Admin view to list all products
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'seller__username', 'category__name']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        if self.request.user.user_type != 'admin':
            return Product.objects.none()
        return Product.objects.all().select_related('seller', 'category')

    def list(self, request, *args, **kwargs):
        if request.user.user_type != 'admin':
            return Response({
                'error': 'Only admins can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin view to manage any product
    """
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Product.objects.all()

    def get_permissions(self):
        if self.request.user.user_type != 'admin':
            return [permissions.DeniedPermission()]
        return super().get_permissions()

    def update(self, request, *args, **kwargs):
        if request.user.user_type != 'admin':
            return Response({
                'error': 'Only admins can update products'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.user_type != 'admin':
            return Response({
                'error': 'Only admins can delete products'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class ProductStatsView(APIView):
    """
    Get product statistics (admin/seller)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.user_type == 'admin':
            # Admin sees all stats
            stats = {
                'total_products': Product.objects.count(),
                'active_products': Product.objects.filter(is_active=True).count(),
                'inactive_products': Product.objects.filter(is_active=False).count(),
                'out_of_stock': Product.objects.filter(stock_quantity=0).count(),
                'total_categories': Category.objects.count(),
                'total_reviews': ProductReview.objects.count(),
                'average_rating': ProductReview.objects.aggregate(
                    avg_rating=Avg('rating')
                )['avg_rating'] or 0
            }
        elif request.user.user_type == 'seller':
            # Seller sees only their stats
            seller_products = Product.objects.filter(seller=request.user)
            stats = {
                'my_products': seller_products.count(),
                'active_products': seller_products.filter(is_active=True).count(),
                'inactive_products': seller_products.filter(is_active=False).count(),
                'out_of_stock': seller_products.filter(stock_quantity=0).count(),
                'total_reviews': ProductReview.objects.filter(
                    product__seller=request.user
                ).count(),
                'average_rating': ProductReview.objects.filter(
                    product__seller=request.user
                ).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
            }
        else:
            return Response({
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)

        return Response(stats)