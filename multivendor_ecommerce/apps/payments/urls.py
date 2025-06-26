# urls.py
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Payment CRUD operations
    path('', views.PaymentListCreateView.as_view(), name='payment-list-create'),
    path('<int:pk>/', views.PaymentDetailView.as_view(), name='payment-detail'),
    
    # Payment by order
    path('order/<int:order_id>/', views.PaymentByOrderView.as_view(), name='payment-by-order'),
    
    # Payment actions
    path('<int:pk>/process/', views.process_payment, name='process-payment'),
    path('<int:pk>/refund/', views.refund_payment, name='refund-payment'),
    
    # User-specific payments
    path('my-payments/', views.UserPaymentListView.as_view(), name='user-payments'),
    
    # Statistics
    path('stats/', views.payment_stats, name='payment-stats'),
]