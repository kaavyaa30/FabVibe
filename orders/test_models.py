from django.test import TestCase
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem, ReturnRequest, ExchangeRequest
from products.models import Product, Category
from decimal import Decimal

User = get_user_model()


class OrderModelTest(TestCase):
    """Test Order model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            description='Test description',
            price=Decimal('99.99'),
            inventory=10
        )
    
    def test_order_creation(self):
        """Test creating an order"""
        order = Order.objects.create(
            user=self.user,
            shipping_address='123 Test St\nTest City, TS 12345',
            payment_method='cod',
            subtotal=Decimal('99.99'),
            total_amount=Decimal('99.99')
        )
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.payment_status, 'pending')
        self.assertIsNotNone(order.order_id)
        self.assertTrue(order.order_id.startswith('ORD-'))
    
    def test_order_id_auto_generation(self):
        """Test order_id is automatically generated"""
        order = Order.objects.create(
            user=self.user,
            shipping_address='123 Test St',
            payment_method='cod',
            subtotal=Decimal('99.99'),
            total_amount=Decimal('99.99')
        )
        self.assertIsNotNone(order.order_id)
        self.assertTrue(order.order_id.startswith('ORD-'))
        self.assertEqual(len(order.order_id), 12)  # ORD- + 8 chars
    
    def test_order_str(self):
        """Test order string representation"""
        order = Order.objects.create(
            user=self.user,
            shipping_address='123 Test St',
            payment_method='cod',
            subtotal=Decimal('99.99'),
            total_amount=Decimal('99.99')
        )
        self.assertEqual(str(order), f"Order {order.order_id}")
    
    def test_order_status_choices(self):
        """Test order status choices"""
        order = Order.objects.create(
            user=self.user,
            shipping_address='123 Test St',
            payment_method='cod',
            status='processing',
            subtotal=Decimal('99.99'),
            total_amount=Decimal('99.99')
        )
        self.assertEqual(order.status, 'processing')
    
    def test_order_payment_method_choices(self):
        """Test payment method choices"""
        order = Order.objects.create(
            user=self.user,
            shipping_address='123 Test St',
            payment_method='upi',
            subtotal=Decimal('99.99'),
            total_amount=Decimal('99.99')
        )
        self.assertEqual(order.payment_method, 'upi')
    
    def test_order_with_tracking_number(self):
        """Test order with tracking number"""
        order = Order.objects.create(
            user=self.user,
            shipping_address='123 Test St',
            payment_method='cod',
            tracking_number='TRACK123456',
            subtotal=Decimal('99.99'),
            total_amount=Decimal('99.99')
        )
        self.assertEqual(order.tracking_number, 'TRACK123456')
    
    def test_order_with_coupon(self):
        """Test order with coupon code"""
        order = Order.objects.create(
            user=self.user,
            shipping_address='123 Test St',
            payment_method='cod',
            coupon_code='SAVE10',
            discount=Decimal('10.00'),
            subtotal=Decimal('99.99'),
            total_amount=Decimal('89.99')
        )
        self.assertEqual(order.coupon_code, 'SAVE10')
        self.assertEqual(order.discount, Decimal('10.00'))


class OrderItemModelTest(TestCase):
    """Test OrderItem model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            description='Test description',
            price=Decimal('99.99'),
            inventory=10
        )
        self.order = Order.objects.create(
            user=self.user,
            shipping_address='123 Test St',
            payment_method='cod',
            subtotal=Decimal('99.99'),
            total_amount=Decimal('99.99')
        )
    
    def test_order_item_creation(self):
        """Test creating an order item"""
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            size='M',
            quantity=2,
            price_at_purchase=Decimal('99.99')
        )
        self.assertEqual(order_item.order, self.order)
        self.assertEqual(order_item.product, self.product)
        self.assertEqual(order_item.size, 'M')
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.price_at_purchase, Decimal('99.99'))
    
    def test_order_item_str(self):
        """Test order item string representation"""
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            size='M',
            quantity=2,
            price_at_purchase=Decimal('99.99')
        )
        self.assertEqual(str(order_item), f"2 x {self.product.name}")
    
    def test_order_item_price_at_purchase(self):
        """Test price_at_purchase preserves historical price"""
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            size='M',
            quantity=1,
            price_at_purchase=Decimal('99.99')
        )
        # Change product price
        self.product.price = Decimal('149.99')
        self.product.save()
        # Order item should still have old price
        order_item.refresh_from_db()
        self.assertEqual(order_item.price_at_purchase, Decimal('99.99'))


class ReturnRequestModelTest(TestCase):
    """Test ReturnRequest model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.order = Order.objects.create(
            user=self.user,
            shipping_address='123 Test St',
            payment_method='cod',
            subtotal=Decimal('99.99'),
            total_amount=Decimal('99.99')
        )
    
    def test_return_request_creation(self):
        """Test creating a return request"""
        return_request = ReturnRequest.objects.create(
            order=self.order,
            reason='Product damaged'
        )
        self.assertEqual(return_request.order, self.order)
        self.assertEqual(return_request.reason, 'Product damaged')
        self.assertEqual(return_request.status, 'pending')
    
    def test_return_request_str(self):
        """Test return request string representation"""
        return_request = ReturnRequest.objects.create(
            order=self.order,
            reason='Product damaged'
        )
        self.assertEqual(str(return_request), f"Return request for {self.order.order_id}")
    
    def test_return_request_status_update(self):
        """Test updating return request status"""
        return_request = ReturnRequest.objects.create(
            order=self.order,
            reason='Product damaged'
        )
        return_request.status = 'approved'
        return_request.admin_notes = 'Approved for return'
        return_request.save()
        self.assertEqual(return_request.status, 'approved')
        self.assertEqual(return_request.admin_notes, 'Approved for return')


class ExchangeRequestModelTest(TestCase):
    """Test ExchangeRequest model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.order = Order.objects.create(
            user=self.user,
            shipping_address='123 Test St',
            payment_method='cod',
            subtotal=Decimal('99.99'),
            total_amount=Decimal('99.99')
        )
    
    def test_exchange_request_creation(self):
        """Test creating an exchange request"""
        exchange_request = ExchangeRequest.objects.create(
            order=self.order,
            reason='Wrong size'
        )
        self.assertEqual(exchange_request.order, self.order)
        self.assertEqual(exchange_request.reason, 'Wrong size')
        self.assertEqual(exchange_request.status, 'pending')
    
    def test_exchange_request_str(self):
        """Test exchange request string representation"""
        exchange_request = ExchangeRequest.objects.create(
            order=self.order,
            reason='Wrong size'
        )
        self.assertEqual(str(exchange_request), f"Exchange request for {self.order.order_id}")
    
    def test_exchange_request_status_update(self):
        """Test updating exchange request status"""
        exchange_request = ExchangeRequest.objects.create(
            order=self.order,
            reason='Wrong size'
        )
        exchange_request.status = 'approved'
        exchange_request.admin_notes = 'Approved for exchange'
        exchange_request.save()
        self.assertEqual(exchange_request.status, 'approved')
        self.assertEqual(exchange_request.admin_notes, 'Approved for exchange')
