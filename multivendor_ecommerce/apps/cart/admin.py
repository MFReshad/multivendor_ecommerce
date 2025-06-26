from django.contrib import admin

# Register your models here.
from .models import Cart, CartItem, Wishlist

admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Wishlist)