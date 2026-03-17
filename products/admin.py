from django.contrib import admin
from .models import Category, Product, ProductImage, ProductSize, ProductColor, Inventory, Wishlist, Banner, Review, InventoryLog

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'parent', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'inventory', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'brand', 'created_at']
    search_fields = ['name', 'description', 'brand']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['-created_at']

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'is_primary', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['product__name']

@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    list_display = ['product', 'size', 'is_available']
    list_filter = ['size', 'is_available']
    search_fields = ['product__name']

@admin.register(ProductColor)
class ProductColorAdmin(admin.ModelAdmin):
    list_display = ['product', 'color_name', 'color_code', 'is_available']
    list_filter = ['is_available']
    search_fields = ['product__name', 'color_name']

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'size', 'quantity', 'low_stock_threshold', 'is_low_stock', 'updated_at']
    list_filter = ['size', 'updated_at']
    search_fields = ['product__name']
    ordering = ['product', 'size']
    
    def is_low_stock(self, obj):
        return obj.is_low_stock()
    is_low_stock.boolean = True
    is_low_stock.short_description = 'Low Stock'

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    search_fields = ['user__email', 'product__name']
    ordering = ['-created_at']

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'display_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title']
    ordering = ['display_order']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['product__name', 'user__email', 'comment']
    ordering = ['-created_at']


@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ['product', 'admin', 'quantity_change', 'reason', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['product__name', 'admin__email', 'reason']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']
