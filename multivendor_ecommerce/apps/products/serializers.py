# apps/products/serializers.py

from rest_framework import serializers
from django.db.models import Avg, Count
from .models import Product, Category, ProductVariant, ProductReview


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for product categories
    """
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at', 'product_count']
        read_only_fields = ['id', 'created_at']

    def get_product_count(self, obj):
        return obj.product_set.filter(is_active=True).count()


class ProductVariantSerializer(serializers.ModelSerializer):
    """
    Serializer for product variants
    """
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'variant_type', 'variant_value', 
            'price_adjustment', 'stock_quantity'
        ]
        read_only_fields = ['id']

    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative")
        return value


class ProductReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for product reviews
    """
    buyer_name = serializers.CharField(source='buyer.username', read_only=True)
    buyer_first_name = serializers.CharField(source='buyer.first_name', read_only=True)

    class Meta:
        model = ProductReview
        fields = [
            'id', 'rating', 'comment', 'created_at',
            'buyer_name', 'buyer_first_name'
        ]
        read_only_fields = ['id', 'created_at', 'buyer_name', 'buyer_first_name']

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


class ProductSerializer(serializers.ModelSerializer):
    """
    Basic product serializer for listing
    """
    seller_name = serializers.CharField(source='seller.username', read_only=True)
    seller_shop_name = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    is_in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock_quantity',
            'image', 'is_active', 'created_at', 'seller_name', 
            'seller_shop_name', 'category_name', 'average_rating',
            'review_count', 'is_in_stock'
        ]
        read_only_fields = [
            'id', 'created_at', 'seller_name', 'seller_shop_name',
            'category_name', 'average_rating', 'review_count', 'is_in_stock'
        ]

    def get_seller_shop_name(self, obj):
        try:
            return obj.seller.sellerprofile.shop_name
        except:
            return obj.seller.username

    def get_average_rating(self, obj):
        if hasattr(obj, 'avg_rating') and obj.avg_rating:
            return round(obj.avg_rating, 1)
        
        avg_rating = obj.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
        return round(avg_rating, 1) if avg_rating else 0

    def get_review_count(self, obj):
        if hasattr(obj, 'review_count'):
            return obj.review_count
        return obj.reviews.count()

    def get_is_in_stock(self, obj):
        return obj.stock_quantity > 0


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Detailed product serializer with all related data
    """
    seller_info = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    is_in_stock = serializers.SerializerMethodField()
    rating_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock_quantity',
            'image', 'is_active', 'created_at', 'seller_info',
            'category', 'variants', 'reviews', 'average_rating',
            'review_count', 'is_in_stock', 'rating_breakdown'
        ]
        read_only_fields = [
            'id', 'created_at', 'seller_info', 'variants', 'reviews',
            'average_rating', 'review_count', 'is_in_stock', 'rating_breakdown'
        ]

    def get_seller_info(self, obj):
        seller_data = {
            'id': obj.seller.id,
            'username': obj.seller.username,
            'shop_name': obj.seller.username
        }
        
        try:
            profile = obj.seller.sellerprofile
            seller_data['shop_name'] = profile.shop_name
            seller_data['shop_description'] = profile.shop_description
        except:
            pass
            
        return seller_data

    def get_average_rating(self, obj):
        avg_rating = obj.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
        return round(avg_rating, 1) if avg_rating else 0

    def get_review_count(self, obj):
        return obj.reviews.count()

    def get_is_in_stock(self, obj):
        return obj.stock_quantity > 0

    def get_rating_breakdown(self, obj):
        """Get breakdown of ratings (5 stars, 4 stars, etc.)"""
        breakdown = {}
        for i in range(1, 6):
            count = obj.reviews.filter(rating=i).count()
            breakdown[f'{i}_star'] = count
        return breakdown


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating products (seller use)
    """
    variants = ProductVariantSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'stock_quantity',
            'image', 'category', 'is_active', 'variants'
        ]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value

    def validate_stock_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative")
        return value

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        product = Product.objects.create(**validated_data)
        
        # Create variants if provided
        for variant_data in variants_data:
            ProductVariant.objects.create(product=product, **variant_data)
        
        return product

    def update(self, instance, validated_data):
        variants_data = validated_data.pop('variants', None)
        
        # Update product fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update variants if provided
        if variants_data is not None:
            # Delete existing variants
            instance.variants.all().delete()
            
            # Create new variants
            for variant_data in variants_data:
                ProductVariant.objects.create(product=instance, **variant_data)
        
        return instance


class ProductSearchSerializer(serializers.Serializer):
    """
    Serializer for product search parameters
    """
    q = serializers.CharField(required=False, help_text="Search query")
    category = serializers.IntegerField(required=False, help_text="Category ID")
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    min_rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    seller = serializers.IntegerField(required=False, help_text="Seller ID")
    page = serializers.IntegerField(min_value=1, default=1)

    def validate(self, data):
        min_price = data.get('min_price')
        max_price = data.get('max_price')
        
        if min_price and max_price and min_price > max_price:
            raise serializers.ValidationError("min_price cannot be greater than max_price")
        
        return data


class SellerProductStatsSerializer(serializers.Serializer):
    """
    Serializer for seller product statistics
    """
    my_products = serializers.IntegerField()
    active_products = serializers.IntegerField()
    inactive_products = serializers.IntegerField()
    out_of_stock = serializers.IntegerField()
    total_reviews = serializers.IntegerField()
    average_rating = serializers.FloatField()


class AdminProductStatsSerializer(serializers.Serializer):
    """
    Serializer for admin product statistics
    """
    total_products = serializers.IntegerField()
    active_products = serializers.IntegerField()
    inactive_products = serializers.IntegerField()
    out_of_stock = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    total_reviews = serializers.IntegerField()
    average_rating = serializers.FloatField()