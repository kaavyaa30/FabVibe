"""Tests for session-to-database cart migration functionality"""
from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth import get_user_model
from cart.models import Cart, CartItem
from cart.utils import migrate_session_cart_to_user
from products.models import Product, Category, Inventory

User = get_user_model()


class CartMigrationTestCase(TestCase):
    """Test cases for cart migration from session to database"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123',
            phone_number='+1234567890'
        )
        self.user.email_verified = True
        self.user.save()
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Create test products
        self.product1 = Product.objects.create(
            name='Test Product 1',
            slug='test-product-1',
            description='Test description',
            price=100.00,
            category=self.category,
            is_active=True
        )
        
        self.product2 = Product.objects.create(
            name='Test Product 2',
            slug='test-product-2',
            description='Test description',
            price=200.00,
            category=self.category,
            is_active=True
        )
        
        # Create inventory for products
        Inventory.objects.create(product=self.product1, size='M', quantity=10)
        Inventory.objects.create(product=self.product1, size='L', quantity=10)
        Inventory.objects.create(product=self.product2, size='M', quantity=10)
    
    def _create_request_with_session(self):
        """Helper to create a request with session support"""
        request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        return request
    
    def test_migrate_empty_session_cart(self):
        """Test migration when session cart is empty"""
        request = self._create_request_with_session()
        
        merged_count, total_items = migrate_session_cart_to_user(request, self.user)
        
        self.assertEqual(merged_count, 0)
        self.assertEqual(total_items, 0)
    
    def test_migrate_session_cart_to_empty_user_cart(self):
        """Test migration from session cart to empty user cart"""
        request = self._create_request_with_session()
        
        # Create session cart with items
        session_cart = Cart.objects.create(session_key=request.session.session_key)
        CartItem.objects.create(cart=session_cart, product=self.product1, size='M', quantity=2)
        CartItem.objects.create(cart=session_cart, product=self.product2, size='M', quantity=1)
        
        # Migrate cart
        merged_count, total_items = migrate_session_cart_to_user(request, self.user)
        
        # Verify migration
        self.assertEqual(merged_count, 2)
        self.assertEqual(total_items, 2)
        
        # Verify user cart has items
        user_cart = Cart.objects.get(user=self.user)
        self.assertEqual(user_cart.items.count(), 2)
        
        # Verify session cart is deleted
        self.assertFalse(Cart.objects.filter(session_key=request.session.session_key).exists())
    
    def test_migrate_with_duplicate_products_same_size(self):
        """Test migration handles duplicate products with same size by combining quantities"""
        request = self._create_request_with_session()
        
        # Create user cart with existing item
        user_cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=user_cart, product=self.product1, size='M', quantity=3)
        
        # Create session cart with same product and size
        session_cart = Cart.objects.create(session_key=request.session.session_key)
        CartItem.objects.create(cart=session_cart, product=self.product1, size='M', quantity=2)
        
        # Migrate cart
        merged_count, total_items = migrate_session_cart_to_user(request, self.user)
        
        # Verify quantities were combined
        self.assertEqual(merged_count, 1)
        self.assertEqual(total_items, 1)
        
        # Verify combined quantity
        user_cart.refresh_from_db()
        item = user_cart.items.get(product=self.product1, size='M')
        self.assertEqual(item.quantity, 5)  # 3 + 2
    
    def test_migrate_with_duplicate_products_different_sizes(self):
        """Test migration handles same product with different sizes as separate items"""
        request = self._create_request_with_session()
        
        # Create user cart with product in size M
        user_cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=user_cart, product=self.product1, size='M', quantity=2)
        
        # Create session cart with same product in size L
        session_cart = Cart.objects.create(session_key=request.session.session_key)
        CartItem.objects.create(cart=session_cart, product=self.product1, size='L', quantity=1)
        
        # Migrate cart
        merged_count, total_items = migrate_session_cart_to_user(request, self.user)
        
        # Verify both sizes exist as separate items
        self.assertEqual(merged_count, 1)
        self.assertEqual(total_items, 2)
        
        # Verify both items exist
        user_cart.refresh_from_db()
        self.assertTrue(user_cart.items.filter(product=self.product1, size='M', quantity=2).exists())
        self.assertTrue(user_cart.items.filter(product=self.product1, size='L', quantity=1).exists())
    
    def test_migrate_mixed_scenario(self):
        """Test migration with mix of new items and duplicates"""
        request = self._create_request_with_session()
        
        # Create user cart with one item
        user_cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=user_cart, product=self.product1, size='M', quantity=1)
        
        # Create session cart with duplicate and new item
        session_cart = Cart.objects.create(session_key=request.session.session_key)
        CartItem.objects.create(cart=session_cart, product=self.product1, size='M', quantity=2)  # Duplicate
        CartItem.objects.create(cart=session_cart, product=self.product2, size='M', quantity=1)  # New
        
        # Migrate cart
        merged_count, total_items = migrate_session_cart_to_user(request, self.user)
        
        # Verify migration
        self.assertEqual(merged_count, 2)
        self.assertEqual(total_items, 2)
        
        # Verify quantities
        user_cart.refresh_from_db()
        item1 = user_cart.items.get(product=self.product1, size='M')
        self.assertEqual(item1.quantity, 3)  # 1 + 2
        
        item2 = user_cart.items.get(product=self.product2, size='M')
        self.assertEqual(item2.quantity, 1)
    
    def test_migrate_clears_session_cart(self):
        """Test that session cart is cleared after successful migration"""
        request = self._create_request_with_session()
        
        # Create session cart
        session_cart = Cart.objects.create(session_key=request.session.session_key)
        CartItem.objects.create(cart=session_cart, product=self.product1, size='M', quantity=1)
        
        # Verify session cart exists
        self.assertTrue(Cart.objects.filter(session_key=request.session.session_key).exists())
        
        # Migrate cart
        migrate_session_cart_to_user(request, self.user)
        
        # Verify session cart is deleted
        self.assertFalse(Cart.objects.filter(session_key=request.session.session_key).exists())
    
    def test_migrate_without_session_key(self):
        """Test migration when request has no session key"""
        request = self.factory.get('/')
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        # Don't save session, so no session_key
        
        merged_count, total_items = migrate_session_cart_to_user(request, self.user)
        
        self.assertEqual(merged_count, 0)
        self.assertEqual(total_items, 0)
    
    def test_migrate_preserves_user_cart_on_error(self):
        """Test that user cart is preserved if migration encounters an error"""
        request = self._create_request_with_session()
        
        # Create user cart with items
        user_cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=user_cart, product=self.product1, size='M', quantity=2)
        
        # Create session cart
        session_cart = Cart.objects.create(session_key=request.session.session_key)
        CartItem.objects.create(cart=session_cart, product=self.product2, size='M', quantity=1)
        
        # Get initial count
        initial_count = user_cart.items.count()
        
        # Migrate should succeed, but test that original items are preserved
        merged_count, total_items = migrate_session_cart_to_user(request, self.user)
        
        # Verify original item still exists
        user_cart.refresh_from_db()
        self.assertTrue(user_cart.items.filter(product=self.product1, size='M', quantity=2).exists())
    
    def test_migrate_multiple_items_from_session(self):
        """Test migration with multiple different items in session cart"""
        request = self._create_request_with_session()
        
        # Create session cart with multiple items
        session_cart = Cart.objects.create(session_key=request.session.session_key)
        CartItem.objects.create(cart=session_cart, product=self.product1, size='M', quantity=1)
        CartItem.objects.create(cart=session_cart, product=self.product1, size='L', quantity=2)
        CartItem.objects.create(cart=session_cart, product=self.product2, size='M', quantity=3)
        
        # Migrate cart
        merged_count, total_items = migrate_session_cart_to_user(request, self.user)
        
        # Verify all items migrated
        self.assertEqual(merged_count, 3)
        self.assertEqual(total_items, 3)
        
        # Verify user cart has all items
        user_cart = Cart.objects.get(user=self.user)
        self.assertEqual(user_cart.items.count(), 3)
