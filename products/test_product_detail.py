"""
Tests for product detail view
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from products.models import Category, Product, ProductImage, ProductSize, Review
from decimal import Decimal

User = get_user_model()


class ProductDetailViewTest(TestCase):
    """Test product detail view functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='+1234567890',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Create product
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            description='Test product description',
            price=Decimal('99.99'),
            brand='Test Brand',
            material='Cotton',
            care_instructions='Machine wash cold',
            inventory=10,
            is_active=True
        )
        
        # Create product images
        self.image1 = ProductImage.objects.create(
            product=self.product,
            image='products/test1.jpg',
            is_primary=True
        )
        self.image2 = ProductImage.objects.create(
            product=self.product,
            image='products/test2.jpg',
            is_primary=False
        )
        
        # Create product sizes
        ProductSize.objects.create(
            product=self.product,
            size='M',
            is_available=True
        )
        ProductSize.objects.create(
            product=self.product,
            size='L',
            is_available=True
        )
        
        # Create review
        Review.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            comment='Great product!'
        )
        
        # Create similar products
        for i in range(5):
            Product.objects.create(
                name=f'Similar Product {i}',
                slug=f'similar-product-{i}',
                category=self.category,
                description=f'Similar product {i} description',
                price=Decimal('89.99'),
                inventory=5,
                is_active=True
            )
    
    def test_product_detail_view_displays_product_info(self):
        """Test that product detail view displays all product information"""
        url = reverse('products:product_detail', kwargs={'product_slug': self.product.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
        self.assertContains(response, self.product.description)
        self.assertContains(response, str(self.product.price))
        self.assertContains(response, self.product.brand)
        self.assertContains(response, self.product.material)
        self.assertContains(response, self.product.care_instructions)
    
    def test_product_detail_view_displays_images(self):
        """Test that product detail view displays all product images"""
        url = reverse('products:product_detail', kwargs={'product_slug': self.product.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that images are in context
        self.assertIn('product_images', response.context)
        self.assertEqual(response.context['product_images'].count(), 2)
    
    def test_product_detail_view_displays_sizes(self):
        """Test that product detail view displays available sizes"""
        url = reverse('products:product_detail', kwargs={'product_slug': self.product.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('available_sizes', response.context)
        available_sizes = list(response.context['available_sizes'])
        self.assertIn('M', available_sizes)
        self.assertIn('L', available_sizes)
    
    def test_product_detail_view_displays_reviews(self):
        """Test that product detail view displays customer reviews"""
        url = reverse('products:product_detail', kwargs={'product_slug': self.product.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('reviews', response.context)
        self.assertEqual(response.context['reviews'].count(), 1)
        self.assertIn('average_rating', response.context)
        self.assertEqual(response.context['average_rating'], 5.0)
        self.assertContains(response, 'Great product!')
    
    def test_product_detail_view_displays_similar_products(self):
        """Test that product detail view displays similar products (4+ items)"""
        url = reverse('products:product_detail', kwargs={'product_slug': self.product.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('similar_products', response.context)
        # Should display at least 4 similar products
        self.assertGreaterEqual(response.context['similar_products'].count(), 4)
        # Should not include the current product
        similar_product_ids = [p.id for p in response.context['similar_products']]
        self.assertNotIn(self.product.id, similar_product_ids)
    
    def test_product_detail_view_inactive_product_returns_404(self):
        """Test that inactive products return 404"""
        self.product.is_active = False
        self.product.save()
        
        url = reverse('products:product_detail', kwargs={'product_slug': self.product.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_product_detail_view_nonexistent_product_returns_404(self):
        """Test that nonexistent products return 404"""
        url = reverse('products:product_detail', kwargs={'product_slug': 'nonexistent-product'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_product_detail_view_wishlist_status_for_authenticated_user(self):
        """Test that wishlist status is shown for authenticated users"""
        self.client.login(email='test@example.com', password='testpass123')
        
        url = reverse('products:product_detail', kwargs={'product_slug': self.product.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('in_wishlist', response.context)
        self.assertFalse(response.context['in_wishlist'])
    
    def test_product_detail_view_image_zoom_functionality(self):
        """Test that image zoom functionality is present in template"""
        url = reverse('products:product_detail', kwargs={'product_slug': self.product.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for zoom-related CSS classes and JavaScript
        self.assertContains(response, 'main-image-container')
        self.assertContains(response, 'zoomed')
    
    def test_product_detail_view_size_chart_link(self):
        """Test that size chart link is present"""
        url = reverse('products:product_detail', kwargs={'product_slug': self.product.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Size Chart')
        self.assertContains(response, 'sizeChartModal')
