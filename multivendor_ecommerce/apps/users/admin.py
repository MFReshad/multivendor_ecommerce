from django.contrib import admin

# Register your models here.

from .models import User, SellerProfile

admin.site.register(User)
admin.site.register(SellerProfile)