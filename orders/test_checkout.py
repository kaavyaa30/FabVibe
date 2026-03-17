from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from users.models import Address
from products.models import Product, Category, Inventory
from cart.models import Cart, CartItem
from decimal import Decimal

User = get_user_model()


class CheckoutViewTests(TestCase):
    """Tests for checkout address selection view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123'
        )
        
        # Create test category and product
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
            is_active=True
        )
        
        # Create inventory
        self.inventory = Inventory.objects.create(
            product=self.product,
            size='M',
            quantity=10
        )
        
        # Create cart with items
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            size='M',
            quantity=2
        )
        
        # Create test address
        self.address = Address.objects.create(
            user=self.user,
            full_name='Test User',
            phone_number='+1234567890',
            address_line1='123 Test St',
            city='Test City',
            state='Test State',
            postal_code='12345',
            country='India',
            is_default=True
        )
    
    def test_checkout_requires_login(self):
        """Test that checkout requires authentication"""
        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/users/login/', response.url)
    
    def test_checkout_displays_saved_addresses(self):
        """Test that checkout displays user's saved addresses"""
        self.client.login(email='test@example.com', password='TestPass123')
        response = self.client.get(reverse('orders:checkout'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test User')
        self.assertContains(response, '123 Test St')
        self.assertContains(response, 'Test City')
    
    def test_checkout_with_empty_cart_redirects(self):
        """Test that checkout with empty cart redirects to cart"""
        # Delete cart items
        self.cart_item.delete()
        
        self.client.login(email='test@example.com', password='TestPass123')
        response = self.client.get(reverse('orders:checkout'))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cart:cart_detail'))
    
    def test_checkout_shows_add_address_form(self):
        """Test that checkout can show add address form"""
        self.client.login(email='test@example.com', password='TestPass123')
        response = self.client.get(reverse('orders:checkout') + '?add_new=true')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Full Name')
        self.assertContains(response, 'Phone Number')
        self.assertContains(response, 'Address Line 1')
    
    def test_select_address_and_proceed(self):
        """Test selecting an address and proceeding to order summary"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        response = self.client.post(reverse('orders:checkout'), {
            'action': 'select_address',
            'address_id': self.address.id
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('orders:order_summary'))
        
        # Check session has selected address
        session = self.client.session
        self.assertEqual(session['selected_address_id'], self.address.id)
    
    def test_select_address_without_id_shows_error(self):
        """Test selecting address without providing ID shows error"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        response = self.client.post(reverse('orders:checkout'), {
            'action': 'select_address'
        })
        
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('select a shipping address', str(messages[0]))
    
    def test_add_new_address_during_checkout(self):
        """Test adding a new address during checkout"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        response = self.client.post(reverse('orders:checkout'), {
            'action': 'add_address',
            'full_name': 'New Address User',
            'phone_number': '+9876543210',
            'address_line1': '456 New St',
            'address_line2': 'Apt 2',
            'city': 'New City',
            'state': 'New State',
            'postal_code': '54321',
            'country': 'India',
            'is_default': False
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('orders:order_summary'))
        
        # Check address was created
        new_address = Address.objects.filter(full_name='New Address User').first()
        self.assertIsNotNone(new_address)
        self.assertEqual(new_address.user, self.user)
        
        # Check session has new address selected
        session = self.client.session
        self.assertEqual(session['selected_address_id'], new_address.id)
    
    def test_add_address_with_invalid_data(self):
        """Test adding address with invalid data shows form errors"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        response = self.client.post(reverse('orders:checkout'), {
            'action': 'add_address',
            'full_name': '',  # Missing required field
            'phone_number': 'invalid',  # Invalid format
            'address_line1': '456 New St',
            'city': 'New City',
            'state': 'New State',
            'postal_code': '54321',
            'country': 'India'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Full Name')
        # Form should be re-rendered with errors
        self.assertTrue(response.context['show_add_form'])
    
    def test_checkout_displays_cart_summary(self):
        """Test that checkout displays cart summary in sidebar"""
        self.client.login(email='test@example.com', password='TestPass123')
        response = self.client.get(reverse('orders:checkout'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Order Summary')
        self.assertContains(response, 'Test Product')
        self.assertContains(response, 'Qty: 2')


class OrderSummaryViewTests(TestCase):
    """Tests for order summary view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123'
        )
        
        # Create test category and product
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
            is_active=True
        )
        
        # Create inventory
        self.inventory = Inventory.objects.create(
            product=self.product,
            size='M',
            quantity=10
        )
        
        # Create cart with items
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            size='M',
            quantity=2
        )
        
        # Create test address
        self.address = Address.objects.create(
            user=self.user,
            full_name='Test User',
            phone_number='+1234567890',
            address_line1='123 Test St',
            city='Test City',
            state='Test State',
            postal_code='12345',
            country='India'
        )
    
    def test_order_summary_requires_login(self):
        """Test that order summary requires authentication"""
        response = self.client.get(reverse('orders:order_summary'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/users/login/', response.url)
    
    def test_order_summary_without_address_redirects(self):
        """Test that order summary without selected address redirects to checkout"""
        self.client.login(email='test@example.com', password='TestPass123')
        response = self.client.get(reverse('orders:order_summary'))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('orders:checkout'))
    
    def test_order_summary_displays_selected_address(self):
        """Test that order summary displays the selected address"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.get(reverse('orders:order_summary'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test User')
        self.assertContains(response, '123 Test St')
        self.assertContains(response, 'Test City')
    
    def test_order_summary_displays_cart_items(self):
        """Test that order summary displays all cart items"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.get(reverse('orders:order_summary'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')
        self.assertContains(response, 'Size: M')
        self.assertContains(response, 'Quantity: 2')
    
    def test_order_summary_calculates_price_breakdown(self):
        """Test that order summary calculates correct price breakdown"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.get(reverse('orders:order_summary'))
        
        self.assertEqual(response.status_code, 200)
        
        # Check price calculations
        subtotal = Decimal('200.00')  # 100 * 2
        tax = subtotal * Decimal('0.18')
        shipping = Decimal('50.00')  # Under 500
        total = subtotal + tax + shipping
        
        self.assertEqual(response.context['subtotal'], subtotal)
        self.assertEqual(response.context['tax'], tax)
        self.assertEqual(response.context['shipping_charge'], shipping)
        self.assertEqual(response.context['total'], total)
    
    def test_order_summary_free_shipping_over_500(self):
        """Test that shipping is free for orders over 500"""
        # Update cart item quantity to make total over 500
        self.cart_item.quantity = 6  # 100 * 6 = 600
        self.cart_item.save()
        
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.get(reverse('orders:order_summary'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['shipping_charge'], Decimal('0'))
        self.assertContains(response, 'FREE')
    
    def test_order_summary_with_empty_cart_redirects(self):
        """Test that order summary with empty cart redirects"""
        # Delete cart items
        self.cart_item.delete()
        
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.get(reverse('orders:order_summary'))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cart:cart_detail'))


class PaymentMethodSelectionViewTests(TestCase):
    """Tests for payment method selection view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123'
        )
        
        # Create test category and product
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
            is_active=True
        )
        
        # Create inventory
        self.inventory = Inventory.objects.create(
            product=self.product,
            size='M',
            quantity=10
        )
        
        # Create cart with items
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            size='M',
            quantity=2
        )
        
        # Create test address
        self.address = Address.objects.create(
            user=self.user,
            full_name='Test User',
            phone_number='+1234567890',
            address_line1='123 Test St',
            city='Test City',
            state='Test State',
            postal_code='12345',
            country='India'
        )
    
    def test_payment_method_selection_requires_login(self):
        """Test that payment method selection requires authentication"""
        response = self.client.get(reverse('orders:payment_method_selection'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/users/login/', response.url)
    
    def test_payment_method_selection_without_address_redirects(self):
        """Test that payment method selection without selected address redirects to checkout"""
        self.client.login(email='test@example.com', password='TestPass123')
        response = self.client.get(reverse('orders:payment_method_selection'))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('orders:checkout'))
    
    def test_payment_method_selection_displays_cod_option(self):
        """Test that payment method selection displays Cash on Delivery option"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.get(reverse('orders:payment_method_selection'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cash on Delivery (COD)')
        self.assertContains(response, 'Pay with cash when your order is delivered')
        self.assertContains(response, 'value="cod"')
    
    def test_payment_method_selection_displays_upi_option(self):
        """Test that payment method selection displays UPI payment option"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.get(reverse('orders:payment_method_selection'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'UPI Payment')
        self.assertContains(response, 'Google Pay, PhonePe, Paytm')
        self.assertContains(response, 'value="upi"')
    
    def test_payment_method_selection_displays_card_option(self):
        """Test that payment method selection displays credit/debit card option"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.get(reverse('orders:payment_method_selection'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Credit / Debit Card')
        self.assertContains(response, 'credit or debit card')
        self.assertContains(response, 'value="card"')
    
    def test_payment_method_selection_displays_order_summary(self):
        """Test that payment method selection displays order summary sidebar"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.get(reverse('orders:payment_method_selection'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Order Summary')
        self.assertContains(response, 'Test User')
        self.assertContains(response, '123 Test St')
        
        # Check price breakdown
        subtotal = Decimal('200.00')
        self.assertEqual(response.context['subtotal'], subtotal)
    
    def test_select_cod_payment_method(self):
        """Test selecting Cash on Delivery payment method"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.post(reverse('orders:payment_method_selection'), {
            'payment_method': 'cod'
        })
        
        # COD creates order immediately and redirects to confirmation
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/orders/order-confirmation/'))
        
        # Check order was created
        from orders.models import Order
        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 1)
        self.assertEqual(orders.first().payment_method, 'cod')
    
    def test_select_upi_payment_method(self):
        """Test selecting UPI payment method"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.post(reverse('orders:payment_method_selection'), {
            'payment_method': 'upi'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Check session has payment method stored
        session = self.client.session
        self.assertEqual(session['payment_method'], 'upi')
    
    def test_select_card_payment_method(self):
        """Test selecting credit/debit card payment method"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.post(reverse('orders:payment_method_selection'), {
            'payment_method': 'card'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Check session has payment method stored
        session = self.client.session
        self.assertEqual(session['payment_method'], 'card')
    
    def test_select_invalid_payment_method(self):
        """Test selecting invalid payment method shows error"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.post(reverse('orders:payment_method_selection'), {
            'payment_method': 'invalid'
        })
        
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('valid payment method', str(messages[0]))
    
    def test_payment_method_selection_with_empty_cart_redirects(self):
        """Test that payment method selection with empty cart redirects"""
        # Delete cart items
        self.cart_item.delete()
        
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.get(reverse('orders:payment_method_selection'))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cart:cart_detail'))
    
    def test_payment_method_selection_displays_progress_indicator(self):
        """Test that payment method selection displays checkout progress"""
        self.client.login(email='test@example.com', password='TestPass123')
        
        # Set selected address in session
        session = self.client.session
        session['selected_address_id'] = self.address.id
        session.save()
        
        response = self.client.get(reverse('orders:payment_method_selection'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Shipping Address')
        self.assertContains(response, 'Order Summary')
        self.assertContains(response, 'Payment')
