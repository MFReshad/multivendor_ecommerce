# apps/users/serializers.py

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, SellerProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    shop_name = serializers.CharField(max_length=100, required=False)
    shop_description = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone', 'address', 'user_type',
            'shop_name', 'shop_description'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        # Validate seller-specific fields
        if attrs.get('user_type') == 'seller':
            if not attrs.get('shop_name'):
                raise serializers.ValidationError("Shop name is required for sellers")
        
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    """
    username = serializers.CharField()
    password = serializers.CharField()


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile display and updates
    """
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'address', 'user_type', 'is_approved', 'date_joined'
        ]
        read_only_fields = ['id', 'username', 'user_type', 'is_approved', 'date_joined']


class SellerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for seller profile
    """
    user_info = UserProfileSerializer(source='user', read_only=True)

    class Meta:
        model = SellerProfile
        fields = [
            'id', 'shop_name', 'shop_description', 'is_approved', 
            'created_at', 'user_info'
        ]
        read_only_fields = ['id', 'is_approved', 'created_at']


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing users (admin view)
    """
    seller_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'password',
            'user_type', 'is_approved', 'is_active', 'date_joined', 'seller_profile'
        ]

    def get_seller_profile(self, obj):
        if obj.user_type == 'seller':
            try:
                profile = obj.sellerprofile
                return {
                    'shop_name': profile.shop_name,
                    'shop_description': profile.shop_description,
                    'is_approved': profile.is_approved
                }
            except SellerProfile.DoesNotExist:
                return None
        return None


class SellerApprovalSerializer(serializers.Serializer):
    """
    Serializer for seller approval/rejection
    """
    seller_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=['approve', 'reject'])


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change
    """
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])