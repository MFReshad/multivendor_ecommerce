from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Count
from .models import Order, OrderItem
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderStatusUpdateSerializer,
    OrderItemSerializer, OrderItemStatusUpdateSerializer
)

class OrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.filter(buyer=user).prefetch_related('items__product', 'items__seller')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Search by order ID or product name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(order_id__icontains=search) |
                Q(items__product__name__icontains=search)
            ).distinct()
        
        return queryset.order_by('-created_at')

class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(buyer=self.request.user).prefetch_related('items__product', 'items__seller')
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return OrderStatusUpdateSerializer
        return OrderSerializer

class SellerOrdersView(generics.ListAPIView):
    """View for sellers to see orders containing their products"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Get orders that contain items sold by this user
        order_ids = OrderItem.objects.filter(seller=user).values_list('order_id', flat=True)
        queryset = Order.objects.filter(id__in=order_ids).prefetch_related('items__product', 'items__seller')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')

class OrderItemListView(generics.ListAPIView):
    """View to get order items for a seller"""
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = OrderItem.objects.filter(seller=user).select_related('order', 'product', 'seller')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by order ID
        order_id = self.request.query_params.get('order_id')
        if order_id:
            queryset = queryset.filter(order__order_id=order_id)
        
        return queryset.order_by('-order__created_at')

class OrderItemUpdateView(generics.UpdateAPIView):
    """Update order item status"""
    serializer_class = OrderItemStatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return OrderItem.objects.filter(seller=self.request.user)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def buyer_order_stats(request):
    """Get order statistics for buyer"""
    user = request.user
    orders = Order.objects.filter(buyer=user)
    
    stats = {
        'total_orders': orders.count(),
        'pending_orders': orders.filter(status='pending').count(),
        'confirmed_orders': orders.filter(status='confirmed').count(),
        'shipped_orders': orders.filter(status='shipped').count(),
        'delivered_orders': orders.filter(status='delivered').count(),
        'cancelled_orders': orders.filter(status='cancelled').count(),
        'total_spent': orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
    }
    
    return Response(stats)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def seller_order_stats(request):
    """Get order statistics for seller"""
    user = request.user
    order_items = OrderItem.objects.filter(seller=user)
    
    stats = {
        'total_items_sold': order_items.count(),
        'pending_items': order_items.filter(status='pending').count(),
        'confirmed_items': order_items.filter(status='confirmed').count(),
        'shipped_items': order_items.filter(status='shipped').count(),
        'delivered_items': order_items.filter(status='delivered').count(),
        'cancelled_items': order_items.filter(status='cancelled').count(),
        'total_revenue': order_items.aggregate(
            total=Sum('price') * Sum('quantity')
        )['total'] or 0,
        'orders_involved': order_items.values('order').distinct().count(),
    }
    
    return Response(stats)

@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_order_status(request, pk):
    """Update order status - only buyer can update"""
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    
    new_status = request.data.get('status')
    if new_status not in dict(Order.STATUS_CHOICES):
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Only allow certain status transitions
    allowed_transitions = {
        'pending': ['cancelled'],
        'confirmed': ['cancelled'],
        'shipped': [],
        'delivered': [],
        'cancelled': []
    }
    
    if new_status not in allowed_transitions.get(order.status, []):
        return Response(
            {'error': f'Cannot change status from {order.status} to {new_status}'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    order.status = new_status
    order.save()
    
    # Update all order items status
    order.items.update(status=new_status)
    
    serializer = OrderSerializer(order, context={'request': request})
    return Response(serializer.data)

@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_order_item_status(request, pk):
    """Update order item status - only seller can update"""
    order_item = get_object_or_404(OrderItem, pk=pk, seller=request.user)
    
    new_status = request.data.get('status')
    if new_status not in dict(Order.STATUS_CHOICES):
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    
    order_item.status = new_status
    order_item.save()
    
    # Check if all items in the order have the same status
    order = order_item.order
    all_items_status = order.items.values_list('status', flat=True).distinct()
    
    if len(all_items_status) == 1:
        # All items have the same status, update order status
        order.status = all_items_status[0]
        order.save()
    
    serializer = OrderItemSerializer(order_item, context={'request': request})
    return Response(serializer.data)

# Admin views
class AdminOrderListView(generics.ListAPIView):
    """Admin view to see all orders"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    queryset = Order.objects.all().prefetch_related('items__product', 'items__seller').order_by('-created_at')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by buyer
        buyer_id = self.request.query_params.get('buyer')
        if buyer_id:
            queryset = queryset.filter(buyer_id=buyer_id)
        
        return queryset