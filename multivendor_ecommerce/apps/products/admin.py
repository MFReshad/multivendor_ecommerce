from django.contrib import admin

# Register your models here.
# Register your models here.
from .models import Category, Product, ProductVariant, ProductReview

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductVariant)
admin.site.register(ProductReview)