# apps/users/views.py

from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.db import transaction
from .models import User, SellerProfile
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserProfileSerializer,
    SellerProfileSerializer,
    UserListSerializer
)

from drf_yasg.utils import swagger_auto_schema

class RegisterView(APIView):
    """
    User registration for buyers and sellers
    """
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=UserRegistrationSerializer)
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # Create user
                    user = User.objects.create(
                        username=serializer.validated_data['username'],
                        email=serializer.validated_data['email'],
                        password=make_password(serializer.validated_data['password']),
                        first_name=serializer.validated_data.get('first_name', ''),
                        last_name=serializer.validated_data.get('last_name', ''),
                        phone=serializer.validated_data.get('phone', ''),
                        address=serializer.validated_data.get('address', ''),
                        user_type=serializer.validated_data['user_type']
                    )
                    
                    # If user is seller, create seller profile
                    if user.user_type == 'seller':
                        SellerProfile.objects.create(
                            user=user,
                            shop_name=serializer.validated_data.get('shop_name', ''),
                            shop_description=serializer.validated_data.get('shop_description', ''),
                            is_approved=False  # Sellers need admin approval
                        )
                        user.is_approved = False
                        user.save()

                    # Generate tokens
                    refresh = RefreshToken.for_user(user)
                    
                    return Response({
                        'message': 'User registered successfully',
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'user_type': user.user_type,
                            'is_approved': user.is_approved
                        },
                        'tokens': {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                        }
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                return Response({
                    'error': 'Registration failed',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    User login for all user types
    """
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(request_body=UserLoginSerializer)
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            user = authenticate(username=username, password=password)
            
            if user:
                # Check if seller is approved
                if user.user_type == 'seller' and not user.is_approved:
                    return Response({
                        'error': 'Your seller account is pending approval'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'message': 'Login successful',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'user_type': user.user_type,
                        'is_approved': user.is_approved
                    },
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    """
    Get and update user profile
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'user': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SellerProfileView(APIView):
    """
    Get and update seller profile (only for sellers)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.user_type != 'seller':
            return Response({
                'error': 'Only sellers can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            seller_profile = SellerProfile.objects.get(user=request.user)
            serializer = SellerProfileSerializer(seller_profile)
            return Response(serializer.data)
        except SellerProfile.DoesNotExist:
            return Response({
                'error': 'Seller profile not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def put(self, request):
        if request.user.user_type != 'seller':
            return Response({
                'error': 'Only sellers can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            seller_profile = SellerProfile.objects.get(user=request.user)
            serializer = SellerProfileSerializer(seller_profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Seller profile updated successfully',
                    'profile': serializer.data
                })
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except SellerProfile.DoesNotExist:
            return Response({
                'error': 'Seller profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class LogoutView(APIView):
    """
    Logout user by blacklisting refresh token
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)


# Admin only views
class AdminUserListView(generics.ListAPIView):
    """
    Admin view to list all users
    """
    serializer_class = UserListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.user_type != 'admin':
            return User.objects.none()
        return User.objects.all().order_by('-date_joined')

    def list(self, request, *args, **kwargs):
        if request.user.user_type != 'admin':
            return Response({
                'error': 'Only admins can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)


class AdminUserDetailView(APIView):
    """
    Admin view to get, update, or delete specific user
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        if request.user.user_type != 'admin':
            return Response({
                'error': 'Only admins can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(id=user_id)
            serializer = UserProfileSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, user_id):
        if request.user.user_type != 'admin':
            return Response({
                'error': 'Only admins can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(id=user_id)
            serializer = UserProfileSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'User updated successfully',
                    'user': serializer.data
                })
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, user_id):
        if request.user.user_type != 'admin':
            return Response({
                'error': 'Only admins can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return Response({
                'message': 'User deleted successfully'
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)


class AdminSellerApprovalView(APIView):
    """
    Admin view to approve or reject seller applications
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get all pending seller applications"""
        if request.user.user_type != 'admin':
            return Response({
                'error': 'Only admins can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        pending_sellers = User.objects.filter(
            user_type='seller', 
            is_approved=False
        ).select_related('sellerprofile')
        
        sellers_data = []
        for seller in pending_sellers:
            try:
                profile = seller.sellerprofile
                sellers_data.append({
                    'id': seller.id,
                    'username': seller.username,
                    'email': seller.email,
                    'shop_name': profile.shop_name,
                    'shop_description': profile.shop_description,
                    'created_at': seller.date_joined
                })
            except SellerProfile.DoesNotExist:
                continue
        
        return Response({
            'pending_sellers': sellers_data
        })

    def post(self, request):
        """Approve or reject seller application"""
        if request.user.user_type != 'admin':
            return Response({
                'error': 'Only admins can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        seller_id = request.data.get('seller_id')
        action = request.data.get('action')  # 'approve' or 'reject'
        
        if not seller_id or action not in ['approve', 'reject']:
            return Response({
                'error': 'Invalid data. Provide seller_id and action (approve/reject)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            seller = User.objects.get(id=seller_id, user_type='seller')
            
            if action == 'approve':
                seller.is_approved = True
                seller.save()
                
                # Update seller profile
                try:
                    profile = seller.sellerprofile
                    profile.is_approved = True
                    profile.save()
                except SellerProfile.DoesNotExist:
                    pass
                
                return Response({
                    'message': f'Seller {seller.username} approved successfully'
                })
            
            else:  # reject
                seller.delete()  # Remove rejected seller
                return Response({
                    'message': f'Seller application rejected and removed'
                })
                
        except User.DoesNotExist:
            return Response({
                'error': 'Seller not found'
            }, status=status.HTTP_404_NOT_FOUND)


class ChangePasswordView(APIView):
    """
    Change user password
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response({
                'error': 'Both old_password and new_password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.check_password(old_password):
            return Response({
                'error': 'Old password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        request.user.password = make_password(new_password)
        request.user.save()
        
        return Response({
            'message': 'Password changed successfully'
        })


class UserStatsView(APIView):
    """
    Get user statistics (for admin dashboard)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.user_type != 'admin':
            return Response({
                'error': 'Only admins can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        stats = {
            'total_users': User.objects.count(),
            'total_buyers': User.objects.filter(user_type='buyer').count(),
            'total_sellers': User.objects.filter(user_type='seller').count(),
            'approved_sellers': User.objects.filter(user_type='seller', is_approved=True).count(),
            'pending_sellers': User.objects.filter(user_type='seller', is_approved=False).count(),
            'total_admins': User.objects.filter(user_type='admin').count(),
        }
        
        return Response(stats)