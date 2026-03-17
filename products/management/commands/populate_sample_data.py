"""
Management command to populate sample data for FabVibe e-commerce platform
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.base import ContentFile
from decimal import Decimal
from datetime import timedelta
import random
import hashlib
import requests

from products.models import Category, Product, ProductImage, ProductSize, ProductColor, Banner, Inventory
from cart.models import Coupon

User = get_user_model()


class ImageGenerator:
    """Generate fashion-related images using Picsum Photos"""
    
    # Image IDs from Picsum for different categories (curated fashion-style images)
    CATEGORY_IMAGE_IDS = {
        'Men': [1, 10, 20, 30, 40],
        'Women': [2, 11, 21, 31, 41],
        'Kids': [3, 12, 22, 32, 42],
        'Accessories': [4, 13, 23, 33, 43],
        'Shirts': [5, 14, 24, 34, 44],
        'T-Shirts': [6, 15, 25, 35, 45],
        'Jeans': [7, 16, 26, 36, 46],
        'Jackets': [8, 17, 27, 37, 47],
        'Shoes': [9, 18, 28, 38, 48],
        'Dresses': [50, 51, 52, 53, 54],
        'Tops': [55, 56, 57, 58, 59],
        'Skirts': [60, 61, 62, 63, 64],
        'Heels': [65, 66, 67, 68, 69],
        'Boys': [70, 71, 72, 73, 74],
        'Girls': [75, 76, 77, 78, 79],
        'Infants': [80, 81, 82, 83, 84],
        'Bags': [85, 86, 87, 88, 89],
        'Belts': [90, 91, 92, 93, 94],
        'Watches': [95, 96, 97, 98, 99],
        'Sunglasses': [100, 101, 102, 103, 104],
    }
    
    @staticmethod
    def get_image_id(name, index=0):
        """Get image ID for category/product"""
        # Check if exact match exists
        if name in ImageGenerator.CATEGORY_IMAGE_IDS:
            ids = ImageGenerator.CATEGORY_IMAGE_IDS[name]
            return ids[index % len(ids)]
        
        # Try to find partial match
        for key, ids in ImageGenerator.CATEGORY_IMAGE_IDS.items():
            if key.lower() in name.lower():
                return ids[index % len(ids)]
        
        # Generate from hash
        hash_val = int(hashlib.md5(f"{name}-{index}".encode()).hexdigest()[:8], 16)
        return (hash_val % 200) + 1
    
    @staticmethod
    def generate_category_image_url(category_name, width=400, height=300):
        """Generate Picsum image URL for category"""
        image_id = ImageGenerator.get_image_id(category_name)
        return f"https://picsum.photos/id/{image_id}/{width}/{height}"
    
    @staticmethod
    def generate_product_image_url(product_name, index=0, width=600, height=800):
        """Generate Picsum image URL for product"""
        image_id = ImageGenerator.get_image_id(product_name, index)
        return f"https://picsum.photos/id/{image_id}/{width}/{height}"
    
    @staticmethod
    def generate_banner_image_url(banner_title, width=1200, height=400):
        """Generate Picsum image URL for banner"""
        image_id = ImageGenerator.get_image_id(banner_title)
        return f"https://picsum.photos/id/{image_id}/{width}/{height}"
    
    @staticmethod
    def download_image(url, filename):
        """Download image from URL"""
        try:
            response = requests.get(url, timeout=15, allow_redirects=True)
            if response.status_code == 200:
                return ContentFile(response.content, name=filename)
        except Exception as e:
            print(f"Error downloading image: {e}")
        return None


class Command(BaseCommand):
    help = 'Populate database with sample data for testing'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting data population...')
        
        # Create admin user
        self.create_admin_user()
        
        # Create categories
        categories = self.create_categories()
        
        # Create products
        products = self.create_products(categories)
        
        # Create banners
        self.create_banners()
        
        # Create coupons
        self.create_coupons()
        
        self.stdout.write(self.style.SUCCESS('Successfully populated sample data!'))
        self.stdout.write(f'Created {len(categories)} categories')
        self.stdout.write(f'Created {len(products)} products')
        self.stdout.write('Created banners and coupons')
    
    def create_admin_user(self):
        """Create admin user if not exists"""
        if not User.objects.filter(email='admin@fabvibe.com').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@fabvibe.com',
                password='admin123',
                phone_number='+1234567890'
            )
            admin.email_verified = True
            admin.save()
            self.stdout.write(self.style.SUCCESS('Created admin user: admin@fabvibe.com / admin123'))
    
    def create_categories(self):
        """Create sample categories with unique images"""
        categories_data = [
            {'name': 'Men', 'subcategories': ['Shirts', 'T-Shirts', 'Jeans', 'Jackets', 'Shoes']},
            {'name': 'Women', 'subcategories': ['Dresses', 'Tops', 'Skirts', 'Heels']},
            {'name': 'Kids', 'subcategories': ['Boys', 'Girls', 'Infants']},
            {'name': 'Accessories', 'subcategories': ['Bags', 'Belts', 'Watches', 'Sunglasses']},
        ]
        
        categories = []
        for cat_data in categories_data:
            # Create parent category
            parent, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'slug': cat_data['name'].lower(), 'is_active': True}
            )
            
            # Add image to parent category if created
            if created and not parent.image:
                image_url = ImageGenerator.generate_category_image_url(parent.name)
                image_file = ImageGenerator.download_image(image_url, f"{parent.slug}.jpg")
                if image_file:
                    parent.image.save(f"{parent.slug}.jpg", image_file, save=True)
                    self.stdout.write(f"  Added image to category: {parent.name}")
            
            categories.append(parent)
            
            # Create subcategories
            for subcat_name in cat_data['subcategories']:
                # Check if subcategory already exists for this parent
                subcat = Category.objects.filter(name=subcat_name, parent=parent).first()
                if not subcat:
                    subcat, created = Category.objects.get_or_create(
                        name=subcat_name,
                        parent=parent,
                        defaults={'slug': f"{parent.slug}-{subcat_name.lower().replace(' ', '-')}", 'is_active': True}
                    )
                    
                    # Add image to subcategory
                    if created and not subcat.image:
                        image_url = ImageGenerator.generate_category_image_url(subcat_name)
                        image_file = ImageGenerator.download_image(image_url, f"{subcat.slug}.jpg")
                        if image_file:
                            subcat.image.save(f"{subcat.slug}.jpg", image_file, save=True)
                            self.stdout.write(f"  Added image to subcategory: {subcat.name}")
                
                categories.append(subcat)
        
        return categories
    
    def create_products(self, categories):
        """Create sample products with realistic Indian market prices"""
        products_data = [
            # Men's products - Realistic Indian prices
            {'name': 'Classic Blue Denim Shirt', 'category': 'Shirts', 'parent': 'Men', 'price': 1299, 'brand': 'Levi\'s'},
            {'name': 'White Cotton Formal Shirt', 'category': 'Shirts', 'parent': 'Men', 'price': 899, 'brand': 'Van Heusen'},
            {'name': 'Black Casual T-Shirt', 'category': 'T-Shirts', 'parent': 'Men', 'price': 499, 'brand': 'Nike'},
            {'name': 'Grey V-Neck T-Shirt', 'category': 'T-Shirts', 'parent': 'Men', 'price': 599, 'brand': 'Adidas'},
            {'name': 'Dark Blue Slim Fit Jeans', 'category': 'Jeans', 'parent': 'Men', 'price': 1899, 'brand': 'Levi\'s'},
            {'name': 'Black Leather Jacket', 'category': 'Jackets', 'parent': 'Men', 'price': 4999, 'brand': 'Zara'},
            
            # Women's products - Realistic Indian prices
            {'name': 'Red Floral Summer Dress', 'category': 'Dresses', 'parent': 'Women', 'price': 1499, 'brand': 'H&M'},
            {'name': 'Blue Denim Dress', 'category': 'Dresses', 'parent': 'Women', 'price': 1299, 'brand': 'Forever 21'},
            {'name': 'White Cotton Top', 'category': 'Tops', 'parent': 'Women', 'price': 699, 'brand': 'Zara'},
            {'name': 'Black Silk Top', 'category': 'Tops', 'parent': 'Women', 'price': 1199, 'brand': 'Mango'},
            {'name': 'High Waist Blue Skirt', 'category': 'Skirts', 'parent': 'Women', 'price': 999, 'brand': 'Levi\'s'},
            
            # Kids products - Realistic Indian prices
            {'name': 'Boys Blue T-Shirt', 'category': 'Boys', 'parent': 'Kids', 'price': 399, 'brand': 'Gap Kids'},
            {'name': 'Girls Pink Dress', 'category': 'Girls', 'parent': 'Kids', 'price': 799, 'brand': 'Gap Kids'},
            {'name': 'Infant Romper Set', 'category': 'Infants', 'parent': 'Kids', 'price': 599, 'brand': 'Carter\'s'},
            
            # Accessories - Realistic Indian prices
            {'name': 'Leather Messenger Bag', 'category': 'Bags', 'parent': 'Accessories', 'price': 2499, 'brand': 'Fossil'},
            {'name': 'Brown Leather Belt', 'category': 'Belts', 'parent': 'Accessories', 'price': 699, 'brand': 'Tommy Hilfiger'},
            {'name': 'Classic Analog Watch', 'category': 'Watches', 'parent': 'Accessories', 'price': 4999, 'brand': 'Fossil'},
        ]
        
        products = []
        sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
        colors = [
            ('Black', '#000000'),
            ('White', '#FFFFFF'),
            ('Blue', '#0000FF'),
            ('Red', '#FF0000'),
            ('Grey', '#808080'),
            ('Navy', '#000080'),
        ]
        
        for prod_data in products_data:
            # Find category
            category = Category.objects.filter(
                name=prod_data['category'],
                parent__name=prod_data['parent']
            ).first()
            if not category:
                self.stdout.write(self.style.WARNING(f"Category not found: {prod_data['parent']} > {prod_data['category']}"))
                continue
            
            # Create product
            product, created = Product.objects.get_or_create(
                name=prod_data['name'],
                defaults={
                    'slug': prod_data['name'].lower().replace(' ', '-').replace('\'', ''),
                    'description': f"High quality {prod_data['name'].lower()} from {prod_data['brand']}. Perfect for everyday wear.",
                    'price': Decimal(str(prod_data['price'])),
                    'category': category,
                    'brand': prod_data['brand'],
                    'material': 'Cotton blend',
                    'care_instructions': 'Machine wash cold, tumble dry low',
                    'is_active': True,
                }
            )
            
            if created:
                # Add product images (2-3 unique images per product)
                num_images = random.randint(2, 3)
                for i in range(num_images):
                    image_url = ImageGenerator.generate_product_image_url(product.name, i)
                    image_file = ImageGenerator.download_image(image_url, f"{product.slug}-{i}.jpg")
                    if image_file:
                        ProductImage.objects.create(
                            product=product,
                            image=image_file,
                            is_primary=(i == 0)
                        )
                        self.stdout.write(f"  Added image {i+1} to product: {product.name}")
                
                # Add sizes
                for size in random.sample(sizes, 4):
                    ProductSize.objects.get_or_create(
                        product=product,
                        size=size,
                        defaults={'is_available': True}
                    )
                    
                    # Add inventory
                    Inventory.objects.get_or_create(
                        product=product,
                        size=size,
                        defaults={
                            'quantity': random.randint(10, 50),
                            'low_stock_threshold': 5
                        }
                    )
                
                # Add colors
                for color_name, color_code in random.sample(colors, 2):
                    ProductColor.objects.get_or_create(
                        product=product,
                        color_name=color_name,
                        defaults={
                            'color_code': color_code,
                            'is_available': True
                        }
                    )
                
                products.append(product)
        
        return products
    
    def create_banners(self):
        """Create sample banners with unique images"""
        banners_data = [
            {'title': 'Summer Sale', 'order': 1, 'link': '/'},
            {'title': 'New Arrivals', 'order': 2, 'link': '/'},
            {'title': 'Special Offer', 'order': 3, 'link': '/'},
        ]
        
        for banner_data in banners_data:
            banner, created = Banner.objects.get_or_create(
                title=banner_data['title'],
                defaults={
                    'link_url': banner_data['link'],
                    'is_active': True,
                    'display_order': banner_data['order']
                }
            )
            
            # Add unique image to banner
            if created and not banner.image:
                image_url = ImageGenerator.generate_banner_image_url(banner.title)
                image_file = ImageGenerator.download_image(image_url, f"banner-{banner.title.lower().replace(' ', '-')}.jpg")
                if image_file:
                    banner.image.save(f"banner-{banner.id}.jpg", image_file, save=True)
                    self.stdout.write(f"  Added image to banner: {banner.title}")
    
    def create_coupons(self):
        """Create sample coupons"""
        now = timezone.now()
        
        coupons_data = [
            {
                'code': 'WELCOME10',
                'discount_type': 'percentage',
                'discount_value': 10,
                'min_purchase_amount': 50,
            },
            {
                'code': 'SAVE20',
                'discount_type': 'percentage',
                'discount_value': 20,
                'min_purchase_amount': 100,
            },
            {
                'code': 'FLAT50',
                'discount_type': 'fixed',
                'discount_value': 50,
                'min_purchase_amount': 200,
            },
        ]
        
        for coupon_data in coupons_data:
            Coupon.objects.get_or_create(
                code=coupon_data['code'],
                defaults={
                    'discount_type': coupon_data['discount_type'],
                    'discount_value': Decimal(str(coupon_data['discount_value'])),
                    'min_purchase_amount': Decimal(str(coupon_data['min_purchase_amount'])),
                    'valid_from': now,
                    'valid_to': now + timedelta(days=30),
                    'is_active': True,
                    'usage_limit': 100,
                    'used_count': 0,
                }
            )
