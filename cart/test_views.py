from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from cart.models import Cart, CartItem
from products.models import Product, Category, Inventory
import json

User = get_user_model()


class CartViewsTestCase(TestCase):
    """Test cart views functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='1234567890',
            password='testpass123'
        )
        self.user.email_verified = True
        self.user.save()
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Create test product
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            description='Test description',
            price=99.99,
            inventory=100
        )
        
        # Create inventory for product
        self.inventory = Inventory.objects.create(
            product=self.product,
            size='M',
            quantity=50
        )
    
    def test_add_to_cart_authenticated(self):
        """Test adding product to cart for authenticated user"""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.post(
            reverse('cart:add_to_cart', args=[self.product.id]),
            data=json.dumps({'size': 'M', 'quantity': 2}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['cart_count'], 1)
        
        # Verify cart item was created
        cart = Cart.objects.get(user=self.user)
        cart_item = CartItem.objects.get(cart=cart, product=self.product)
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(cart_item.size, 'M')
    
    def test_add_to_cart_guest(self):
        """Test adding product to cart for guest user"""
        response = self.client.post(
            reverse('cart:add_to_cart', args=[self.product.id]),
            data=json.dumps({'size': 'M', 'quantity': 1}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify cart was created with session key
        self.assertTrue(Cart.objects.filter(session_key__isnull=False).exists())
    
    def test_add_to_cart_without_size(self):
        """Test adding product without size returns error"""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.post(
            reverse('cart:add_to_cart', args=[self.product.id]),
            data=json.dumps({'quantity': 1}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Size is required', data['error'])
    
    def test_add_to_cart_out_of_stock(self):
        """Test adding out of stock product returns error"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Set inventory to 0
        self.inventory.quantity = 0
        self.inventory.save()
        
        response = self.client.post(
            reverse('cart:add_to_cart', args=[self.product.id]),
            data=json.dumps({'size': 'M', 'quantity': 1}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('out of stock', data['error'])
    
    def test_add_to_cart_exceeds_inventory(self):
        """Test adding quantity exceeding inventory returns error"""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.post(
            reverse('cart:add_to_cart', args=[self.product.id]),
            data=json.dumps({'size': 'M', 'quantity': 100}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('available in stock', data['error'])
    
    def test_add_to_cart_updates_existing_item(self):
        """Test adding same product updates quantity"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Add product first time
        self.client.post(
            reverse('cart:add_to_cart', args=[self.product.id]),
            data=json.dumps({'size': 'M', 'quantity': 2}),
            content_type='application/json'
        )
        
        # Add same product again
        response = self.client.post(
            reverse('cart:add_to_cart', args=[self.product.id]),
            data=json.dumps({'size': 'M', 'quantity': 3}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify quantity was updated
        cart = Cart.objects.get(user=self.user)
        cart_item = CartItem.objects.get(cart=cart, product=self.product)
        self.assertEqual(cart_item.quantity, 5)
    
    def test_update_cart_item(self):
        """Test updating cart item quantity"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Create cart and item
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            size='M',
            quantity=2
        )
        
        # Update quantity
        response = self.client.post(
            reverse('cart:update_cart_item', args=[cart_item.id]),
            data=json.dumps({'quantity': 5}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify quantity was updated
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 5)
    
    def test_update_cart_item_invalid_quantity(self):
        """Test updating cart item with invalid quantity"""
        self.client.login(email='test@example.com', password='testpass123')
        
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            size='M',
            quantity=2
        )
        
        response = self.client.post(
            reverse('cart:update_cart_item', args=[cart_item.id]),
            data=json.dumps({'quantity': 0}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_remove_from_cart(self):
        """Test removing item from cart"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Create cart and item
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            size='M',
            quantity=2
        )
        
        # Remove item
        response = self.client.post(
            reverse('cart:remove_from_cart', args=[cart_item.id]),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify item was deleted
        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())
    
    def test_cart_detail_authenticated(self):
        """Test cart detail view for authenticated user"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Create cart and item
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            size='M',
            quantity=2
        )
        
        response = self.client.get(reverse('cart:cart_detail'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')
        self.assertContains(response, '$99.99')
    
    def test_cart_detail_empty(self):
        """Test cart detail view with empty cart"""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(reverse('cart:cart_detail'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your cart is empty')
    
    def test_cart_total_calculation(self):
        """Test cart total is calculated correctly"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Create cart with multiple items
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            size='M',
            quantity=2
        )
        
        # Create another product
        product2 = Product.objects.create(
            name='Test Product 2',
            slug='test-product-2',
            category=self.category,
            description='Test description 2',
            price=49.99,
            inventory=100
        )
        
        CartItem.objects.create(
            cart=cart,
            product=product2,
            size='L',
            quantity=1
        )
        
        # Calculate expected total: (99.99 * 2) + (49.99 * 1) = 249.97
        expected_total = 249.97
        self.assertAlmostEqual(float(cart.get_total()), expected_total, places=2)
