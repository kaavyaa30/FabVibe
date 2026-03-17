from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Category(models.Model):
    """Product category model"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        ordering = ['name']


class Product(models.Model):
    """Product model"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    brand = models.CharField(max_length=100, blank=True)
    material = models.CharField(max_length=200, blank=True)
    care_instructions = models.TextField(blank=True)
    inventory = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def is_in_stock(self):
        return self.inventory > 0
    
    def is_low_stock(self):
        return 0 < self.inventory <= settings.LOW_STOCK_THRESHOLD
    
    class Meta:
        db_table = 'products'
        ordering = ['-created_at']


class ProductImage(models.Model):
    """Product image model"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for {self.product.name}"
    
    class Meta:
        db_table = 'product_images'
        ordering = ['-is_primary', 'created_at']


class ProductSize(models.Model):
    """Product size model"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sizes')
    size = models.CharField(max_length=10)
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.size}"
    
    class Meta:
        db_table = 'product_sizes'
        unique_together = ['product', 'size']


class ProductColor(models.Model):
    """Product color model"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='colors')
    color_name = models.CharField(max_length=50)
    color_code = models.CharField(max_length=7)  # Hex color code
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.color_name}"
    
    class Meta:
        db_table = 'product_colors'
        unique_together = ['product', 'color_name']


class Inventory(models.Model):
    """Inventory tracking model for product sizes"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_items')
    size = models.CharField(max_length=10)
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.size} (Qty: {self.quantity})"
    
    def is_in_stock(self):
        """Check if item is in stock"""
        return self.quantity > 0
    
    def is_low_stock(self):
        """Check if item is below low stock threshold"""
        return 0 < self.quantity <= self.low_stock_threshold
    
    class Meta:
        db_table = 'inventory'
        verbose_name_plural = 'Inventory'
        unique_together = ['product', 'size']
        ordering = ['product', 'size']



class Wishlist(models.Model):
    """Wishlist model"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name}"
    
    class Meta:
        db_table = 'wishlist'
        unique_together = ['user', 'product']
        ordering = ['-created_at']


class Banner(models.Model):
    """Homepage banner model"""
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='banners/')
    link_url = models.URLField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        db_table = 'banners'
        ordering = ['display_order', '-created_at']


class Review(models.Model):
    """Product review model"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name} ({self.rating}★)"
    
    class Meta:
        db_table = 'reviews'
        unique_together = ['product', 'user']
        ordering = ['-created_at']


class InventoryLog(models.Model):
    """Inventory change log model"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_logs')
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_change = models.IntegerField()  # Positive for additions, negative for reductions
    reason = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity_change:+d} units at {self.timestamp}"
    
    class Meta:
        db_table = 'inventory_logs'
        ordering = ['-timestamp']
