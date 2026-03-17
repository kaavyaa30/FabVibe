from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from products.models import Product, Category, Inventory
from cart.models import Cart, CartItem
from users.models import Address
from orders.models import Order, OrderItem
from decimal import Decimal

User = get_user_model()


class CODPaymentTests(TestCase):
    """Tests for Cash on Delivery payment processing"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123'
        )
        
        # Create category and product
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            description='Test description',
            price=Decimal('100.00'),
            category=self.category,
            inventory=10
        )
        
        # Create inventory for the product
        self.inventory = Inventory.objects.create(
            product=self.product,
            size='M',
            quantity=10
        )
        
        # Create address
        self.address = Address.objects.create(
            user=self.user,
            full_name='Test User',
            phone_number='1234567890',
            address_line1='123 Test St',
            city='Test City',
            state='Test State',
            postal_code='12345',
            is_default=True
        )
        
        # Create cart with items
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            size='M',
            quantity=2
        )
    
    def test_cod_creates_order_immediately(self):
        """Test that COD payment creates order immediately"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        # Submit COD payment
        response = self.client.post(reverse('orders:payment_method_selection'), {
            'payment_method': 'cod'
        })
        
        # Should redirect to order confirmation
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/orders/order-confirmation/'))
        
        # Check order was created
        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 1)
        
        order = orders.first()
        self.assertEqual(order.payment_method, 'cod')
        self.assertEqual(order.payment_status, 'pending')
        self.assertEqual(order.status, 'pending')
        
        # Check order items were created
        order_items = order.items.all()
        self.assertEqual(order_items.count(), 1)
        self.assertEqual(order_items.first().product, self.product)
        self.assertEqual(order_items.first().quantity, 2)
    
    def test_cod_clears_cart_after_order(self):
        """Test that COD payment clears cart after order creation"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        # Verify cart has items
        self.assertEqual(self.cart.items.count(), 1)
        
        # Submit COD payment
        response = self.client.post(reverse('orders:payment_method_selection'), {
            'payment_method': 'cod'
        })
        
        # Cart should be empty
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.items.count(), 0)
    
    def test_cod_clears_session_data(self):
        """Test that COD payment clears session data"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        # Submit COD payment
        response = self.client.post(reverse('orders:payment_method_selection'), {
            'payment_method': 'cod'
        })
        
        # Session should not have selected_address_id
        session = self.client.session
        self.assertNotIn('selected_address_id', session)
    
    def test_cod_calculates_correct_totals(self):
        """Test that COD order has correct price calculations"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        # Submit COD payment
        response = self.client.post(reverse('orders:payment_method_selection'), {
            'payment_method': 'cod'
        })
        
        # Check order totals
        order = Order.objects.get(user=self.user)
        
        # Subtotal should be 2 * 100 = 200
        self.assertEqual(order.subtotal, Decimal('200.00'))
        
        # Tax should be 18% of subtotal = 36
        self.assertEqual(order.tax, Decimal('36.00'))
        
        # Shipping should be 0 (free over 500) or 50 (under 500)
        # Since subtotal is 200, shipping should be 50
        self.assertEqual(order.shipping_charge, Decimal('50.00'))
        
        # Total should be subtotal + tax + shipping = 200 + 36 + 50 = 286
        self.assertEqual(order.total_amount, Decimal('286.00'))


class OnlinePaymentTests(TestCase):
    """Tests for online payment processing (UPI/Card)"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123'
        )
        
        # Create category and product
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            description='Test description',
            price=Decimal('100.00'),
            category=self.category,
            inventory=10
        )
        
        # Create inventory for the product
        self.inventory = Inventory.objects.create(
            product=self.product,
            size='M',
            quantity=10
        )
        
        # Create address
        self.address = Address.objects.create(
            user=self.user,
            full_name='Test User',
            phone_number='1234567890',
            address_line1='123 Test St',
            city='Test City',
            state='Test State',
            postal_code='12345',
            is_default=True
        )
        
        # Create cart with items
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            size='M',
            quantity=2
        )
    
    def test_upi_redirects_to_payment_gateway(self):
        """Test that UPI payment redirects to payment gateway"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        # Submit UPI payment
        response = self.client.post(reverse('orders:payment_method_selection'), {
            'payment_method': 'upi'
        })
        
        # Should redirect to payment processing
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('orders:process_payment'))
        
        # Session should have payment method and pricing
        session = self.client.session
        self.assertEqual(session['payment_method'], 'upi')
        self.assertIn('order_pricing', session)
    
    def test_card_redirects_to_payment_gateway(self):
        """Test that card payment redirects to payment gateway"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        # Submit card payment
        response = self.client.post(reverse('orders:payment_method_selection'), {
            'payment_method': 'card'
        })
        
        # Should redirect to payment processing
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('orders:process_payment'))
        
        # Session should have payment method and pricing
        session = self.client.session
        self.assertEqual(session['payment_method'], 'card')
        self.assertIn('order_pricing', session)
    
    def test_payment_success_creates_order(self):
        """Test that successful payment creates order"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set up session data
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session['payment_method'] = 'upi'
        session['order_pricing'] = {
            'subtotal': '200.00',
            'tax': '36.00',
            'shipping_charge': '50.00',
            'total': '286.00',
        }
        session.save()
        
        # Simulate successful payment
        response = self.client.post(reverse('orders:process_payment'), {
            'action': 'simulate_success'
        })
        
        # Should redirect to order confirmation
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/orders/order-confirmation/'))
        
        # Check order was created
        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 1)
        
        order = orders.first()
        self.assertEqual(order.payment_method, 'upi')
        self.assertEqual(order.payment_status, 'completed')
        self.assertEqual(order.status, 'pending')
    
    def test_payment_failure_redirects_back(self):
        """Test that payment failure redirects back to payment method selection"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set up session data
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session['payment_method'] = 'upi'
        session['order_pricing'] = {
            'subtotal': '200.00',
            'tax': '36.00',
            'shipping_charge': '50.00',
            'total': '286.00',
        }
        session.save()
        
        # Simulate payment failure
        response = self.client.post(reverse('orders:process_payment'), {
            'action': 'simulate_failure'
        })
        
        # Should redirect back to payment method selection
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('orders:payment_method_selection'))
        
        # No order should be created
        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 0)
    
    def test_payment_success_clears_cart(self):
        """Test that successful payment clears cart"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set up session data
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session['payment_method'] = 'upi'
        session['order_pricing'] = {
            'subtotal': '200.00',
            'tax': '36.00',
            'shipping_charge': '50.00',
            'total': '286.00',
        }
        session.save()
        
        # Verify cart has items
        self.assertEqual(self.cart.items.count(), 1)
        
        # Simulate successful payment
        response = self.client.post(reverse('orders:process_payment'), {
            'action': 'simulate_success'
        })
        
        # Cart should be empty
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.items.count(), 0)


class OrderConfirmationTests(TestCase):
    """Tests for order confirmation page"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123'
        )
        
        # Create category and product
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            description='Test description',
            price=Decimal('100.00'),
            category=self.category,
            inventory=10
        )
        
        # Create order
        self.order = Order.objects.create(
            user=self.user,
            shipping_address='Test User\n123 Test St\nTest City, Test State 12345\nPhone: 1234567890',
            payment_method='cod',
            payment_status='pending',
            subtotal=Decimal('200.00'),
            tax=Decimal('36.00'),
            shipping_charge=Decimal('50.00'),
            total_amount=Decimal('286.00'),
            status='pending'
        )
        
        # Create order item
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            size='M',
            quantity=2,
            price_at_purchase=Decimal('100.00')
        )
    
    def test_order_confirmation_displays_order_details(self):
        """Test that order confirmation displays order details"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        response = self.client.get(reverse('orders:order_confirmation', args=[self.order.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_id)
        self.assertContains(response, 'Order Placed Successfully')
    
    def test_order_confirmation_displays_order_items(self):
        """Test that order confirmation displays order items"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        response = self.client.get(reverse('orders:order_confirmation', args=[self.order.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
        self.assertContains(response, 'M')  # Size
        self.assertContains(response, '2')  # Quantity
    
    def test_order_confirmation_displays_price_breakdown(self):
        """Test that order confirmation displays price breakdown"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        response = self.client.get(reverse('orders:order_confirmation', args=[self.order.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '200.00')  # Subtotal
        self.assertContains(response, '36.00')   # Tax
        self.assertContains(response, '50.00')   # Shipping
        self.assertContains(response, '286.00')  # Total
    
    def test_order_confirmation_requires_login(self):
        """Test that order confirmation requires authentication"""
        response = self.client.get(reverse('orders:order_confirmation', args=[self.order.id]))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/users/login/'))
    
    def test_order_confirmation_only_shows_own_orders(self):
        """Test that users can only view their own orders"""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='TestPass123'
        )
        
        # Login as other user
        self.client.login(email='other@example.com', password='TestPass123')
        
        # Try to access first user's order
        response = self.client.get(reverse('orders:order_confirmation', args=[self.order.id]))
        
        # Should return 404
        self.assertEqual(response.status_code, 404)
