from rest_framework import serializers
from .models import Order, OrderItem
from apps.products.models import Product
from apps.users.models import User

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.SerializerMethodField()
    seller_name = serializers.CharField(source='seller.username', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_image', 
            'seller', 'seller_name', 'quantity', 'price', 'status'
        ]
        read_only_fields = ['id']
    
    def get_product_image(self, obj):
        if obj.product.image:
            return self.context['request'].build_absolute_uri(obj.product.image.url)
        return None

class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product', 'seller', 'quantity', 'price']
    
    def validate(self, data):
        product = data['product']
        quantity = data['quantity']
        
        # Check if product is available
        if not product.is_active:
            raise serializers.ValidationError("Product is not available")
        
        # Check stock availability
        if hasattr(product, 'stock') and product.stock < quantity:
            raise serializers.ValidationError("Insufficient stock")
        
        return data

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    buyer_name = serializers.CharField(source='buyer.username', read_only=True)
    buyer_email = serializers.CharField(source='buyer.email', read_only=True)
    total_items = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'buyer', 'buyer_name', 'buyer_email',
            'total_amount', 'status', 'shipping_address', 
            'created_at', 'updated_at', 'items', 'total_items'
        ]
        read_only_fields = ['id', 'order_id', 'created_at', 'updated_at']
    
    def get_total_items(self, obj):
        return obj.items.count()

class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True)
    
    class Meta:
        model = Order
        fields = ['shipping_address', 'items']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        request = self.context['request']
        
        # Generate unique order ID
        import uuid
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate total amount
        total_amount = sum(item['quantity'] * item['price'] for item in items_data)
        
        # Create order
        order = Order.objects.create(
            buyer=request.user,
            order_id=order_id,
            total_amount=total_amount,
            **validated_data
        )
        
        # Create order items
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        
        return order

class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']

class OrderItemStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['status']