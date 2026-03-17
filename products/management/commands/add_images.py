"""
Management command to add images to existing categories, products, and banners
"""
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
import hashlib
import requests
import random

from products.models import Category, Product, ProductImage, Banner


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
            else:
                print(f"Failed to download image: HTTP {response.status_code}")
        except Exception as e:
            print(f"Error downloading image from {url}: {e}")
        return None


class Command(BaseCommand):
    help = 'Add unique images to existing categories, products, and banners'

    def handle(self, *args, **kwargs):
        self.stdout.write('Adding images to existing data...')
        
        # Add images to categories
        self.add_category_images()
        
        # Add images to products
        self.add_product_images()
        
        # Add images to banners
        self.add_banner_images()
        
        self.stdout.write(self.style.SUCCESS('Successfully added images!'))
    
    def add_category_images(self):
        """Add images to categories without images"""
        categories = Category.objects.all()
        count = 0
        
        for category in categories:
            if not category.image:
                image_url = ImageGenerator.generate_category_image_url(category.name)
                image_file = ImageGenerator.download_image(image_url, f"{category.slug}.jpg")
                if image_file:
                    category.image.save(f"{category.slug}.jpg", image_file, save=True)
                    self.stdout.write(f"  ✓ Added image to category: {category.name}")
                    count += 1
        
        self.stdout.write(self.style.SUCCESS(f"Added images to {count} categories"))
    
    def add_product_images(self):
        """Add images to products without images"""
        products = Product.objects.all()
        count = 0
        
        for product in products:
            # Check if product has images
            existing_images = ProductImage.objects.filter(product=product).count()
            
            if existing_images == 0:
                # Add 2-3 unique images per product
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
                        self.stdout.write(f"  ✓ Added image {i+1} to product: {product.name}")
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f"Added images to {count} products"))
    
    def add_banner_images(self):
        """Add images to banners without images"""
        banners = Banner.objects.all()
        count = 0
        
        for banner in banners:
            if not banner.image:
                image_url = ImageGenerator.generate_banner_image_url(banner.title)
                image_file = ImageGenerator.download_image(image_url, f"banner-{banner.title.lower().replace(' ', '-')}.jpg")
                if image_file:
                    banner.image.save(f"banner-{banner.id}.jpg", image_file, save=True)
                    self.stdout.write(f"  ✓ Added image to banner: {banner.title}")
                    count += 1
        
        self.stdout.write(self.style.SUCCESS(f"Added images to {count} banners"))
