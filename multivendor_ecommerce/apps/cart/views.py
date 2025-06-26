from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Sum, F
from .models import Cart, CartItem, Wishlist
from apps.products.models import Product
from .serializers import (
    CartSerializer, CartItemSerializer, CartItemCreateUpdateSerializer,
    WishlistSerializer, WishlistProductSerializer
)

class CartView(generics.RetrieveAPIView):
    """Get user's cart"""
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart

class CartItemListView(generics.ListAPIView):
    """List all items in user's cart"""
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart.items.select_related('product', 'product__seller').order_by('-added_at')

class CartItemCreateView(generics.CreateAPIView):
    """Add item to cart"""
    serializer_class = CartItemCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']
        
        # Check if item already exists in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Update quantity if item already exists
            cart_item.quantity = quantity
            cart_item.save()
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return updated cart
        cart = Cart.objects.get(user=request.user)
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data, status=status.HTTP_201_CREATED)

class CartItemUpdateView(generics.UpdateAPIView):
    """Update cart item quantity"""
    serializer_class = CartItemCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart.items.all()
    
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        
        # Return updated cart item
        cart_item = self.get_object()
        serializer = CartItemSerializer(cart_item, context={'request': request})
        return Response(serializer.data)

class CartItemDeleteView(generics.DestroyAPIView):
    """Remove item from cart"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart.items.all()
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        
        # Return updated cart
        cart = Cart.objects.get(user=request.user)
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_to_cart(request):
    """Add product to cart with quantity"""
    product_id = request.data.get('product_id')
    quantity = request.data.get('quantity', 1)
    
    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Check if item already exists
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    serializer = CartItemSerializer(cart_item, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_cart_item_quantity(request, item_id):
    """Update specific cart item quantity"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_item = cart.items.get(id=item_id)
    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        return Response({'error': 'Cart item not found'}, status=status.HTTP_404_NOT_FOUND)
    
    quantity = request.data.get('quantity')
    if not quantity or quantity <= 0:
        return Response({'error': 'Invalid quantity'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check stock availability
    if hasattr(cart_item.product, 'stock') and cart_item.product.stock < quantity:
        return Response(
            {'error': f'Only {cart_item.product.stock} items available'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    cart_item.quantity = quantity
    cart_item.save()
    
    serializer = CartItemSerializer(cart_item, context={'request': request})
    return Response(serializer.data)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def clear_cart(request):
    """Clear all items from cart"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart.items.all().delete()
        
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data)
    except Cart.DoesNotExist:
        return Response({'message': 'Cart is already empty'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def cart_summary(request):
    """Get cart summary with totals"""
    try:
        cart = Cart.objects.get(user=request.user)
        items = cart.items.select_related('product')
        
        summary = {
            'total_items': sum(item.quantity for item in items),
            'unique_items': items.count(),
            'total_price': sum(item.quantity * item.product.price for item in items),
            'items_by_seller': {}
        }
        
        # Group items by seller
        for item in items:
            seller = item.product.seller.username
            if seller not in summary['items_by_seller']:
                summary['items_by_seller'][seller] = {
                    'items': [],
                    'total_price': 0
                }
            
            item_data = {
                'product_name': item.product.name,
                'quantity': item.quantity,
                'price': item.product.price,
                'total': item.quantity * item.product.price
            }
            
            summary['items_by_seller'][seller]['items'].append(item_data)
            summary['items_by_seller'][seller]['total_price'] += item_data['total']
        
        return Response(summary)
    
    except Cart.DoesNotExist:
        return Response({
            'total_items': 0,
            'unique_items': 0,
            'total_price': 0,
            'items_by_seller': {}
        })

# Wishlist Views
class WishlistView(generics.RetrieveAPIView):
    """Get user's wishlist"""
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        wishlist, created = Wishlist.objects.get_or_create(user=self.request.user)
        return wishlist

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_to_wishlist(request):
    """Add product to wishlist"""
    product_id = request.data.get('product_id')
    
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    wishlist.products.add(product)
    
    return Response({'message': 'Product added to wishlist'}, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist"""
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        product = Product.objects.get(id=product_id)
        wishlist.products.remove(product)
        
        return Response({'message': 'Product removed from wishlist'}, status=status.HTTP_200_OK)
    except (Wishlist.DoesNotExist, Product.DoesNotExist):
        return Response({'error': 'Product or wishlist not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def move_to_cart(request, product_id):
    """Move product from wishlist to cart"""
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        product = Product.objects.get(id=product_id)
        
        # Add to cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': 1}
        )
        
        if not created:
            cart_item.quantity += 1
            cart_item.save()
        
        # Remove from wishlist
        wishlist.products.remove(product)
        
        return Response({'message': 'Product moved to cart'}, status=status.HTTP_200_OK)
    
    except (Wishlist.DoesNotExist, Product.DoesNotExist):
        return Response({'error': 'Product or wishlist not found'}, status=status.HTTP_404_NOT_FOUND)
