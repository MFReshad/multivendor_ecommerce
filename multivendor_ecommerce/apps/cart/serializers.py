from rest_framework import serializers
from .models import Cart, CartItem, Wishlist
from apps.products.models import Product

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    product_image = serializers.SerializerMethodField()
    product_stock = serializers.IntegerField(source='product.stock', read_only=True)
    seller_name = serializers.CharField(source='product.seller.username', read_only=True)
    total_price = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_name', 'product_price', 'product_image',
            'product_stock', 'seller_name', 'quantity', 'total_price', 
            'is_available', 'added_at'
        ]
        read_only_fields = ['id', 'added_at']
    
    def get_product_image(self, obj):
        if obj.product.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.product.image.url)
        return None
    
    def get_total_price(self, obj):
        return obj.quantity * obj.product.price
    
    def get_is_available(self, obj):
        return obj.product.is_active and (not hasattr(obj.product, 'stock') or obj.product.stock >= obj.quantity)

class CartItemCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['product', 'quantity']
    
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value
    
    def validate(self, data):
        product = data['product']
        quantity = data['quantity']
        
        # Check if product is active
        if not product.is_active:
            raise serializers.ValidationError("This product is not available")
        
        # Check stock availability
        if hasattr(product, 'stock') and product.stock < quantity:
            raise serializers.ValidationError(f"Only {product.stock} items available in stock")
        
        return data

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    unique_items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'items', 'total_items', 'total_price', 
            'unique_items_count', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']
    
    def get_total_items(self, obj):
        return sum(item.quantity for item in obj.items.all())
    
    def get_total_price(self, obj):
        return sum(item.quantity * item.product.price for item in obj.items.all())
    
    def get_unique_items_count(self, obj):
        return obj.items.count()

class WishlistProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    seller_name = serializers.CharField(source='seller.username', read_only=True)
    is_in_cart = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'image', 'seller_name', 
            'is_active', 'is_in_cart', 'created_at'
        ]
    
    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None
    
    def get_is_in_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                cart = Cart.objects.get(user=request.user)
                return cart.items.filter(product=obj).exists()
            except Cart.DoesNotExist:
                return False
        return False

class WishlistSerializer(serializers.ModelSerializer):
    products = WishlistProductSerializer(many=True, read_only=True)
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Wishlist
        fields = ['id', 'user', 'products', 'products_count', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
    
    def get_products_count(self, obj):
        return obj.products.count()
