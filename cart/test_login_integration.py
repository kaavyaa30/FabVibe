"""Integration tests for cart migration during login"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from cart.models import Cart, CartItem
from products.models import Product, Category, Inventory

User = get_user_model()


class LoginCartMigrationIntegrationTestCase(TestCase):
    """Integration tests for cart migration during user login"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
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
        
        # Create inventory
        Inventory.objects.create(product=self.product1, size='M', quantity=10)
        Inventory.objects.create(product=self.product2, size='L', quantity=10)
    
    def test_login_migrates_session_cart(self):
        """Test that logging in migrates session cart to user cart"""
        # Add items to cart as guest
        session = self.client.session
        session.save()
        
        session_cart = Cart.objects.create(session_key=session.session_key)
        CartItem.objects.create(cart=session_cart, product=self.product1, size='M', quantity=2)
        
        # Login
        response = self.client.post(reverse('users:login'), {
            'username': 'test@example.com',
            'password': 'TestPass123'
        })
        
        # Verify redirect
        self.assertEqual(response.status_code, 302)
        
        # Verify user cart has items
        user_cart = Cart.objects.filter(user=self.user).first()
        self.assertIsNotNone(user_cart)
        self.assertEqual(user_cart.items.count(), 1)
        
        # Verify session cart is deleted
        self.assertFalse(Cart.objects.filter(session_key=session.session_key).exists())
    
    def test_login_merges_duplicate_items(self):
        """Test that login merges duplicate items from session and user carts"""
        # Create existing user cart
        user_cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=user_cart, product=self.product1, size='M', quantity=1)
        
        # Add same item to session cart
        session = self.client.session
        session.save()
        
        session_cart = Cart.objects.create(session_key=session.session_key)
        CartItem.objects.create(cart=session_cart, product=self.product1, size='M', quantity=2)
        
        # Login
        self.client.post(reverse('users:login'), {
            'username': 'test@example.com',
            'password': 'TestPass123'
        })
        
        # Verify quantities were merged
        user_cart.refresh_from_db()
        item = user_cart.items.get(product=self.product1, size='M')
        self.assertEqual(item.quantity, 3)  # 1 + 2
    
    def test_login_shows_merge_message(self):
        """Test that login shows appropriate message when items are merged"""
        # Add items to session cart
        session = self.client.session
        session.save()
        
        session_cart = Cart.objects.create(session_key=session.session_key)
        CartItem.objects.create(cart=session_cart, product=self.product1, size='M', quantity=1)
        CartItem.objects.create(cart=session_cart, product=self.product2, size='L', quantity=1)
        
        # Login
        response = self.client.post(reverse('users:login'), {
            'username': 'test@example.com',
            'password': 'TestPass123'
        }, follow=True)
        
        # Verify success message mentions merged items
        messages = list(response.context['messages'])
        self.assertTrue(any('2 item(s) from your cart have been restored' in str(m) for m in messages))
    
    def test_login_without_session_cart_shows_normal_message(self):
        """Test that login without session cart shows normal welcome message"""
        # Login without session cart
        response = self.client.post(reverse('users:login'), {
            'username': 'test@example.com',
            'password': 'TestPass123'
        }, follow=True)
        
        # Verify normal welcome message
        messages = list(response.context['messages'])
        self.assertTrue(any('Welcome back' in str(m) for m in messages))
    
    def test_login_with_phone_number_migrates_cart(self):
        """Test that login with phone number also migrates cart"""
        # Add items to session cart
        session = self.client.session
        session.save()
        
        session_cart = Cart.objects.create(session_key=session.session_key)
        CartItem.objects.create(cart=session_cart, product=self.product1, size='M', quantity=1)
        
        # Login with phone number
        response = self.client.post(reverse('users:login'), {
            'username': '+1234567890',
            'password': 'TestPass123'
        })
        
        # Verify redirect
        self.assertEqual(response.status_code, 302)
        
        # Verify cart was migrated
        user_cart = Cart.objects.filter(user=self.user).first()
        self.assertIsNotNone(user_cart)
        self.assertEqual(user_cart.items.count(), 1)
    
    def test_failed_login_preserves_session_cart(self):
        """Test that failed login preserves session cart"""
        # Add items to session cart
        session = self.client.session
        session.save()
        
        session_cart = Cart.objects.create(session_key=session.session_key)
        CartItem.objects.create(cart=session_cart, product=self.product1, size='M', quantity=1)
        
        # Attempt login with wrong password
        response = self.client.post(reverse('users:login'), {
            'username': 'test@example.com',
            'password': 'WrongPassword'
        })
        
        # Verify session cart still exists
        self.assertTrue(Cart.objects.filter(session_key=session.session_key).exists())
        self.assertEqual(session_cart.items.count(), 1)
    
    def test_login_with_empty_session_cart_does_not_error(self):
        """Test that login with empty session cart completes successfully"""
        # Create empty session cart
        session = self.client.session
        session.save()
        
        Cart.objects.create(session_key=session.session_key)
        
        # Login
        response = self.client.post(reverse('users:login'), {
            'username': 'test@example.com',
            'password': 'TestPass123'
        })
        
        # Verify successful login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
