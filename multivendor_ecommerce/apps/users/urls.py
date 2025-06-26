# apps/users/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    
    # Profile Management
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('seller-profile/', views.SellerProfileView.as_view(), name='seller-profile'),
    
    # Admin Only Views
    path('admin/users/', views.AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/user/<int:user_id>/', views.AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/seller-approval/', views.AdminSellerApprovalView.as_view(), name='admin-seller-approval'),
    path('admin/stats/', views.UserStatsView.as_view(), name='admin-user-stats'),
]