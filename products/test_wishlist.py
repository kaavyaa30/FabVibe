"""
Tests for wishlist functionality
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from products.models import Product, Category, Wishlist
import json

User = get_user_model()


class WishlistViewTests(TestCase):
    """Test wishlist views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Create test products
        self.product1 = Product.objects.create(
            name='Test Product 1',
            slug='test-product-1',
            category=self.category,
            description='Test description 1',
            price=29.99,
            inventory=10
        )
        
        self.product2 = Product.objects.create(
            name='Test Product 2',
            slug='test-product-2',
            category=self.category,
            description='Test description 2',
            price=39.99,
            inventory=5
        )
    
    def test_wishlist_page_requires_login(self):
        """Test that wishlist page requires authentication"""
        response = self.client.get(reverse('products:wishlist'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('/users/login/', response.url)
    
    def test_wishlist_page_authenticated(self):
        """Test that authenticated users can access wishlist page"""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('products:wishlist'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/wishlist.html')
    
    def test_add_to_wishlist_requires_login(self):
        """Test that adding to wishlist requires authentication"""
        response = self.client.post(
            reverse('products:add_to_wishlist', args=[self.product1.id])
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_add_to_wishlist_success(self):
        """Test successfully adding product to wishlist"""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.post(
            reverse('products:add_to_wishlist', args=[self.product1.id]),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(data['in_wishlist'])
        self.assertEqual(data['message'], 'Product added to wishlist')
        
        # Verify product is in wishlist
        self.assertTrue(
            Wishlist.objects.filter(user=self.user, product=self.product1).exists()
        )
    
    def test_add_to_wishlist_toggle_remove(self):
        """Test that adding an already wishlisted product removes it (toggle)"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # First add to wishlist
        Wishlist.objects.create(user=self.user, product=self.product1)
        
        # Try to add again (should remove)
        response = self.client.post(
            reverse('products:add_to_wishlist', args=[self.product1.id]),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(data['in_wishlist'])
        self.assertEqual(data['message'], 'Product removed from wishlist')
        
        # Verify product is not in wishlist
        self.assertFalse(
            Wishlist.objects.filter(user=self.user, product=self.product1).exists()
        )
    
    def test_add_to_wishlist_invalid_product(self):
        """Test adding non-existent product to wishlist"""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.post(
            reverse('products:add_to_wishlist', args=[99999]),
            content_type='application/json'
        )
        
        # Should return 400 because the view catches the exception
        self.assertIn(response.status_code, [400, 404])
    
    def test_add_to_wishlist_inactive_product(self):
        """Test adding inactive product to wishlist"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Make product inactive
        self.product1.is_active = False
        self.product1.save()
        
        response = self.client.post(
            reverse('products:add_to_wishlist', args=[self.product1.id]),
            content_type='application/json'
        )
        
        # Should return 400 because the view catches the exception
        self.assertIn(response.status_code, [400, 404])
    
    def test_remove_from_wishlist_success(self):
        """Test successfully removing product from wishlist"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Add product to wishlist first
        Wishlist.objects.create(user=self.user, product=self.product1)
        
        response = self.client.post(
            reverse('products:remove_from_wishlist', args=[self.product1.id]),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Product removed from wishlist')
        
        # Verify product is not in wishlist
        self.assertFalse(
            Wishlist.objects.filter(user=self.user, product=self.product1).exists()
        )
    
    def test_remove_from_wishlist_not_in_wishlist(self):
        """Test removing product that's not in wishlist"""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.post(
            reverse('products:remove_from_wishlist', args=[self.product1.id]),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
    
    def test_get_wishlist_items_empty(self):
        """Test getting empty wishlist items"""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(reverse('products:get_wishlist_items'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['items']), 0)
    
    def test_get_wishlist_items_with_products(self):
        """Test getting wishlist items with products"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Add products to wishlist
        Wishlist.objects.create(user=self.user, product=self.product1)
        Wishlist.objects.create(user=self.user, product=self.product2)
        
        response = self.client.get(reverse('products:get_wishlist_items'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['items']), 2)
        
        # Check item structure
        item = data['items'][0]
        self.assertIn('product_id', item)
        self.assertIn('name', item)
        self.assertIn('price', item)
        self.assertIn('image_url', item)
        self.assertIn('product_url', item)
        self.assertIn('in_stock', item)
        self.assertIn('added_at', item)
    
    def test_wishlist_persistence_across_sessions(self):
        """Test that wishlist persists across sessions for authenticated users"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Add product to wishlist
        self.client.post(
            reverse('products:add_to_wishlist', args=[self.product1.id]),
            content_type='application/json'
        )
        
        # Logout
        self.client.logout()
        
        # Login again
        self.client.login(email='test@example.com', password='testpass123')
        
        # Check wishlist still has the product
        response = self.client.get(reverse('products:get_wishlist_items'))
        data = json.loads(response.content)
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['product_id'], self.product1.id)
    
    def test_wishlist_unique_per_user(self):
        """Test that wishlist is unique per user"""
        # Create another user
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123',
            phone_number='0987654321'
        )
        
        # User 1 adds product to wishlist
        self.client.login(email='test@example.com', password='testpass123')
        self.client.post(
            reverse('products:add_to_wishlist', args=[self.product1.id]),
            content_type='application/json'
        )
        self.client.logout()
        
        # User 2 checks their wishlist (should be empty)
        self.client.login(email='test2@example.com', password='testpass123')
        response = self.client.get(reverse('products:get_wishlist_items'))
        data = json.loads(response.content)
        self.assertEqual(len(data['items']), 0)
    
    def test_product_detail_shows_wishlist_status(self):
        """Test that product detail page shows correct wishlist status"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Add product to wishlist
        Wishlist.objects.create(user=self.user, product=self.product1)
        
        # Check product detail page
        response = self.client.get(
            reverse('products:product_detail', args=[self.product1.slug])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['in_wishlist'])
    
    def test_home_page_shows_wishlist_ids(self):
        """Test that home page includes user's wishlist product IDs"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Add product to wishlist
        Wishlist.objects.create(user=self.user, product=self.product1)
        
        # Check home page
        response = self.client.get(reverse('products:home'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_wishlist_ids', response.context)
        self.assertIn(self.product1.id, response.context['user_wishlist_ids'])
    
    def test_category_page_shows_wishlist_ids(self):
        """Test that category page includes user's wishlist product IDs"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Add product to wishlist
        Wishlist.objects.create(user=self.user, product=self.product1)
        
        # Check category page
        response = self.client.get(
            reverse('products:category_products', args=[self.category.slug])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_wishlist_ids', response.context)
        self.assertIn(self.product1.id, response.context['user_wishlist_ids'])
    
    def test_search_page_shows_wishlist_ids(self):
        """Test that search page includes user's wishlist product IDs"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Add product to wishlist
        Wishlist.objects.create(user=self.user, product=self.product1)
        
        # Check search page
        response = self.client.get(
            reverse('products:search') + '?q=Test'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_wishlist_ids', response.context)
        self.assertIn(self.product1.id, response.context['user_wishlist_ids'])
    
    def test_wishlist_display_with_multiple_products(self):
        """Test that wishlist page displays multiple products correctly"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Add multiple products to wishlist
        Wishlist.objects.create(user=self.user, product=self.product1)
        Wishlist.objects.create(user=self.user, product=self.product2)
        
        # Get wishlist items
        response = self.client.get(reverse('products:get_wishlist_items'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['items']), 2)
        
        # Verify all required fields are present
        for item in data['items']:
            self.assertIn('product_id', item)
            self.assertIn('name', item)
            self.assertIn('price', item)
            self.assertIn('image_url', item)
            self.assertIn('product_url', item)
            self.assertIn('in_stock', item)
            self.assertIn('added_at', item)
    
    def test_wishlist_display_with_out_of_stock_product(self):
        """Test that wishlist correctly shows out of stock status"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Make product out of stock
        self.product1.inventory = 0
        self.product1.save()
        
        # Add to wishlist
        Wishlist.objects.create(user=self.user, product=self.product1)
        
        # Get wishlist items
        response = self.client.get(reverse('products:get_wishlist_items'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['items']), 1)
        self.assertFalse(data['items'][0]['in_stock'])
    
    def test_wishlist_persistence_after_logout_login(self):
        """Test that wishlist persists after logout and login"""
        # Login and add products
        self.client.login(email='test@example.com', password='testpass123')
        self.client.post(
            reverse('products:add_to_wishlist', args=[self.product1.id]),
            content_type='application/json'
        )
        self.client.post(
            reverse('products:add_to_wishlist', args=[self.product2.id]),
            content_type='application/json'
        )
        
        # Logout
        self.client.logout()
        
        # Login again
        self.client.login(email='test@example.com', password='testpass123')
        
        # Verify wishlist still has both products
        response = self.client.get(reverse('products:get_wishlist_items'))
        data = json.loads(response.content)
        self.assertEqual(len(data['items']), 2)
        
        product_ids = [item['product_id'] for item in data['items']]
        self.assertIn(self.product1.id, product_ids)
        self.assertIn(self.product2.id, product_ids)


class WishlistModelTests(TestCase):
    """Test Wishlist model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            description='Test description',
            price=29.99,
            inventory=10
        )
    
    def test_wishlist_creation(self):
        """Test creating a wishlist item"""
        wishlist_item = Wishlist.objects.create(
            user=self.user,
            product=self.product
        )
        
        self.assertEqual(wishlist_item.user, self.user)
        self.assertEqual(wishlist_item.product, self.product)
        self.assertIsNotNone(wishlist_item.created_at)
    
    def test_wishlist_str_representation(self):
        """Test string representation of wishlist item"""
        wishlist_item = Wishlist.objects.create(
            user=self.user,
            product=self.product
        )
        
        expected = f"{self.user.email} - {self.product.name}"
        self.assertEqual(str(wishlist_item), expected)
    
    def test_wishlist_unique_constraint(self):
        """Test that user cannot add same product twice"""
        Wishlist.objects.create(user=self.user, product=self.product)
        
        # Try to create duplicate
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Wishlist.objects.create(user=self.user, product=self.product)
    
    def test_wishlist_ordering(self):
        """Test that wishlist items are ordered by created_at descending"""
        product2 = Product.objects.create(
            name='Test Product 2',
            slug='test-product-2',
            category=self.category,
            description='Test description 2',
            price=39.99,
            inventory=5
        )
        
        item1 = Wishlist.objects.create(user=self.user, product=self.product)
        # Add a small delay to ensure different timestamps
        import time
        time.sleep(0.01)
        item2 = Wishlist.objects.create(user=self.user, product=product2)
        
        wishlist_items = list(Wishlist.objects.filter(user=self.user))
        # Most recent should be first
        self.assertEqual(wishlist_items[0].product, product2)
        self.assertEqual(wishlist_items[1].product, self.product)
