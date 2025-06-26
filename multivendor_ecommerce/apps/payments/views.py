# views.py
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db import models
from .models import Payment
from .serializers import (
    PaymentSerializer,
    PaymentCreateSerializer,
    PaymentUpdateSerializer,
    PaymentListSerializer
)


class PaymentListCreateView(generics.ListCreateAPIView):
    """
    GET: List all payments with filtering and search
    POST: Create a new payment
    """
    queryset = Payment.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method', 'order__id']
    search_fields = ['order__order_id', 'stripe_payment_intent_id']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PaymentCreateSerializer
        return PaymentListSerializer


class PaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific payment
    PUT/PATCH: Update a payment
    DELETE: Delete a payment
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PaymentUpdateSerializer
        return PaymentSerializer


class PaymentByOrderView(generics.RetrieveAPIView):
    """
    GET: Retrieve payment by order ID
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        order_id = self.kwargs['order_id']
        return get_object_or_404(Payment, order__id=order_id)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_payment(request, pk):
    """
    Process a payment (update status to completed)
    """
    try:
        payment = Payment.objects.get(pk=pk)
    except Payment.DoesNotExist:
        return Response(
            {'error': 'Payment not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )

    if payment.status != 'pending':
        return Response(
            {'error': 'Payment is not in pending status'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    payment.status = 'completed'
    payment.save()

    serializer = PaymentSerializer(payment)
    return Response(
        {
            'message': 'Payment processed successfully',
            'payment': serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refund_payment(request, pk):
    """
    Refund a payment (update status to refunded)
    """
    try:
        payment = Payment.objects.get(pk=pk)
    except Payment.DoesNotExist:
        return Response(
            {'error': 'Payment not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )

    if payment.status != 'completed':
        return Response(
            {'error': 'Can only refund completed payments'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    payment.status = 'refunded'
    payment.save()

    serializer = PaymentSerializer(payment)
    return Response(
        {
            'message': 'Payment refunded successfully',
            'payment': serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_stats(request):
    """
    Get payment statistics
    """
    from django.db.models import Count, Sum
    
    stats = Payment.objects.aggregate(
        total_payments=Count('id'),
        total_amount=Sum('amount'),
        pending_count=Count('id', filter=models.Q(status='pending')),
        completed_count=Count('id', filter=models.Q(status='completed')),
        failed_count=Count('id', filter=models.Q(status='failed')),
        refunded_count=Count('id', filter=models.Q(status='refunded'))
    )
    
    # Payment method breakdown
    payment_methods = Payment.objects.values('payment_method').annotate(
        count=Count('id'),
        total_amount=Sum('amount')
    )
    
    return Response({
        'summary': stats,
        'payment_methods': payment_methods
    })


class UserPaymentListView(generics.ListAPIView):
    """
    GET: List payments for the authenticated user's orders
    """
    serializer_class = PaymentListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']

    def get_queryset(self):
        return Payment.objects.filter(order__customer=self.request.user)