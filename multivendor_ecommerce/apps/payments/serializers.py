# serializers.py
from rest_framework import serializers
from .models import Payment
from apps.orders.serializers import OrderSerializer


class PaymentSerializer(serializers.ModelSerializer):
    order_details = OrderSerializer(source='order', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'order',
            'order_details',
            'stripe_payment_intent_id',
            'amount',
            'status',
            'status_display',
            'payment_method',
            'payment_method_display',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'order_details', 'status_display', 'payment_method_display']


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'order',
            'stripe_payment_intent_id',
            'amount',
            'payment_method'
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


class PaymentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'status',
            'stripe_payment_intent_id'
        ]

    def validate_status(self, value):
        # Prevent certain status transitions
        if self.instance and self.instance.status == 'completed' and value != 'refunded':
            raise serializers.ValidationError("Cannot change status from completed except to refunded")
        return value


class PaymentListSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='order.order_id', read_only=True)
    customer_name = serializers.CharField(source='order.customer.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'order_id',
            'customer_name',
            'amount',
            'status',
            'status_display',
            'payment_method',
            'payment_method_display',
            'created_at'
        ]