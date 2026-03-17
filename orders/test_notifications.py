from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core import mail
from orders.models import Order, OrderItem
from orders.tasks import (
    send_order_confirmation_email,
    send_order_confirmation_sms,
    send_order_status_update_email,
    send_order_status_update_sms
)
from products.models import Product, Category
from decimal import Decimal

User = get_user_model()


class OrderConfirmationEmailTests(TestCase):
    """Tests for order confirmation email sending"""
    
    def setUp(self):
        """Set up test data"""
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='+1234567890',
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
            category=self.category
        )
        
        # Create order
        self.order = Order.objects.create(
            user=self.user,
            shipping_address='Test User\n123 Test St\nTest City, TS 12345\nPhone: 1234567890',
            payment_method='cod',
            payment_status='pending',
            subtotal=Decimal('200.00'),
            tax=Decimal('36.00'),
            shipping_charge=Decimal('50.00'),
            total_amount=Decimal('286.00'),
            status='pending'
        )
        
        # Create order item
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            size='M',
            quantity=2,
            price_at_purchase=Decimal('100.00')
        )
    
    def test_send_order_confirmation_email(self):
        """Test that order confirmation email is sent"""
        # Send email
        result = send_order_confirmation_email(self.order.id)
        
        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)
        
        # Check email details
        email = mail.outbox[0]
        self.assertIn('Order Confirmation', email.subject)
        self.assertIn(self.order.order_id, email.subject)
        self.assertEqual(email.to, [self.user.email])
        self.assertIn(self.order.order_id, email.body)
        self.assertIn('Test Product', email.body)
    
    def test_send_order_confirmation_email_with_invalid_order(self):
        """Test email sending with invalid order ID"""
        result = send_order_confirmation_email(99999)
        self.assertIn('not found', result)
        self.assertEqual(len(mail.outbox), 0)
    
    def test_order_confirmation_email_contains_order_details(self):
        """Test that email contains all order details"""
        send_order_confirmation_email(self.order.id)
        
        email = mail.outbox[0]
        # Check for order details
        self.assertIn(self.order.order_id, email.body)
        self.assertIn('Test Product', email.body)
        self.assertIn('200.00', email.body)  # Subtotal
        self.assertIn('36.00', email.body)   # Tax
        self.assertIn('50.00', email.body)   # Shipping
        self.assertIn('286.00', email.body)  # Total
    
    def test_order_confirmation_email_contains_shipping_address(self):
        """Test that email contains shipping address"""
        send_order_confirmation_email(self.order.id)
        
        email = mail.outbox[0]
        self.assertIn('123 Test St', email.body)
        self.assertIn('Test City', email.body)


class OrderConfirmationSMSTests(TestCase):
    """Tests for order confirmation SMS sending"""
    
    def setUp(self):
        """Set up test data"""
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='+1234567890',
            password='TestPass123'
        )
        
        # Create order
        self.order = Order.objects.create(
            user=self.user,
            shipping_address='Test Address',
            payment_method='cod',
            payment_status='pending',
            subtotal=Decimal('200.00'),
            tax=Decimal('36.00'),
            shipping_charge=Decimal('50.00'),
            total_amount=Decimal('286.00'),
            status='pending'
        )
    
    def test_send_order_confirmation_sms(self):
        """Test that order confirmation SMS is sent"""
        result = send_order_confirmation_sms(self.order.id)
        
        # Check result message
        self.assertIn('sent successfully', result)
        self.assertIn(self.user.phone_number, result)
    
    def test_send_order_confirmation_sms_with_invalid_order(self):
        """Test SMS sending with invalid order ID"""
        result = send_order_confirmation_sms(99999)
        self.assertIn('not found', result)
    
    def test_send_order_confirmation_sms_without_phone(self):
        """Test SMS sending when user has no phone number"""
        # Remove phone number
        self.user.phone_number = ''
        self.user.save()
        
        result = send_order_confirmation_sms(self.order.id)
        self.assertIn('No phone number', result)


class OrderStatusUpdateEmailTests(TestCase):
    """Tests for order status update email sending"""
    
    def setUp(self):
        """Set up test data"""
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='+1234567890',
            password='TestPass123'
        )
        
        # Create order
        self.order = Order.objects.create(
            user=self.user,
            shipping_address='Test Address',
            payment_method='cod',
            payment_status='pending',
            subtotal=Decimal('200.00'),
            tax=Decimal('36.00'),
            shipping_charge=Decimal('50.00'),
            total_amount=Decimal('286.00'),
            status='pending'
        )
    
    def test_send_order_status_update_email(self):
        """Test that status update email is sent"""
        # Update order status
        self.order.status = 'shipped'
        self.order.tracking_number = 'TRACK123456'
        self.order.save()
        
        # Send email
        result = send_order_status_update_email(self.order.id)
        
        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)
        
        # Check email details
        email = mail.outbox[0]
        self.assertIn('Order Status Update', email.subject)
        self.assertIn(self.order.order_id, email.subject)
        self.assertEqual(email.to, [self.user.email])
        self.assertIn(self.order.order_id, email.body)
        self.assertIn('TRACK123456', email.body)
    
    def test_send_order_status_update_email_with_invalid_order(self):
        """Test email sending with invalid order ID"""
        result = send_order_status_update_email(99999)
        self.assertIn('not found', result)
        self.assertEqual(len(mail.outbox), 0)


class OrderStatusUpdateSMSTests(TestCase):
    """Tests for order status update SMS sending"""
    
    def setUp(self):
        """Set up test data"""
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='+1234567890',
            password='TestPass123'
        )
        
        # Create order
        self.order = Order.objects.create(
            user=self.user,
            shipping_address='Test Address',
            payment_method='cod',
            payment_status='pending',
            subtotal=Decimal('200.00'),
            tax=Decimal('36.00'),
            shipping_charge=Decimal('50.00'),
            total_amount=Decimal('286.00'),
            status='pending'
        )
    
    def test_send_order_status_update_sms_shipped(self):
        """Test SMS for shipped status"""
        self.order.status = 'shipped'
        self.order.tracking_number = 'TRACK123'
        self.order.save()
        
        result = send_order_status_update_sms(self.order.id)
        self.assertIn('SMS sent', result)
    
    def test_send_order_status_update_sms_delivered(self):
        """Test SMS for delivered status"""
        self.order.status = 'delivered'
        self.order.save()
        
        result = send_order_status_update_sms(self.order.id)
        self.assertIn('SMS sent', result)
    
    def test_send_order_status_update_sms_out_for_delivery(self):
        """Test SMS for out for delivery status"""
        self.order.status = 'out_for_delivery'
        self.order.save()
        
        result = send_order_status_update_sms(self.order.id)
        self.assertIn('SMS sent', result)
    
    def test_send_order_status_update_sms_processing(self):
        """Test SMS for processing status"""
        self.order.status = 'processing'
        self.order.save()
        
        result = send_order_status_update_sms(self.order.id)
        self.assertIn('SMS sent', result)
    
    def test_send_order_status_update_sms_cancelled(self):
        """Test SMS for cancelled status"""
        self.order.status = 'cancelled'
        self.order.save()
        
        result = send_order_status_update_sms(self.order.id)
        self.assertIn('SMS sent', result)
    
    def test_send_order_status_update_sms_with_invalid_order(self):
        """Test SMS sending with invalid order ID"""
        result = send_order_status_update_sms(99999)
        self.assertIn('not found', result)
    
    def test_send_order_status_update_sms_without_phone(self):
        """Test SMS sending when user has no phone number"""
        # Remove phone number
        self.user.phone_number = ''
        self.user.save()
        
        result = send_order_status_update_sms(self.order.id)
        self.assertIn('No phone number', result)


class OrderConfirmationIntegrationTests(TestCase):
    """Integration tests for order confirmation flow"""
    
    def setUp(self):
        """Set up test data"""
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='+1234567890',
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
            category=self.category
        )
        
        # Create order
        self.order = Order.objects.create(
            user=self.user,
            shipping_address='Test User\n123 Test St\nTest City, TS 12345',
            payment_method='cod',
            payment_status='pending',
            subtotal=Decimal('200.00'),
            tax=Decimal('36.00'),
            shipping_charge=Decimal('50.00'),
            total_amount=Decimal('286.00'),
            status='pending'
        )
        
        # Create order item
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            size='M',
            quantity=2,
            price_at_purchase=Decimal('100.00')
        )
    
    def test_order_confirmation_sends_both_email_and_sms(self):
        """Test that both email and SMS are sent on order confirmation"""
        # Send both notifications
        email_result = send_order_confirmation_email(self.order.id)
        sms_result = send_order_confirmation_sms(self.order.id)
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('sent successfully', email_result)
        
        # Check SMS was sent
        self.assertIn('sent successfully', sms_result)
    
    def test_order_id_is_unique(self):
        """Test that each order gets a unique order ID"""
        order2 = Order.objects.create(
            user=self.user,
            shipping_address='Test Address',
            payment_method='upi',
            payment_status='completed',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            status='pending'
        )
        
        self.assertNotEqual(self.order.order_id, order2.order_id)
        self.assertTrue(self.order.order_id.startswith('ORD-'))
        self.assertTrue(order2.order_id.startswith('ORD-'))
    
    def test_order_confirmation_includes_estimated_delivery(self):
        """Test that order confirmation includes estimated delivery information"""
        send_order_confirmation_email(self.order.id)
        
        email = mail.outbox[0]
        self.assertIn('5-7 business days', email.body)
