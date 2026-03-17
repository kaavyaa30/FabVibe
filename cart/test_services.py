"""Tests for cart price calculation service"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from cart.models import Cart, CartItem
from cart.services import PriceCalculator
from products.models import Product, Category, Inventory

User = get_user_model()


class PriceCalculatorTestCase(TestCase):
    """Test cases for PriceCalculator service"""
    
    def setUp(self):
        """Set up test data"""
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        # Create category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Create products
        self.product1 = Product.objects.create(
            name='Test Product 1',
            slug='test-product-1',
            description='Test description',
            price=Decimal('100.00'),
            category=self.category,
            is_active=True
        )
        
        self.product2 = Product.objects.create(
            name='Test Product 2',
            slug='test-product-2',
            description='Test description',
            price=Decimal('200.00'),
            category=self.category,
            is_active=True
        )
        
        # Create inventory
        Inventory.objects.create(
            product=self.product1,
            size='M',
            quantity=10
        )
        
        Inventory.objects.create(
            product=self.product2,
            size='L',
            quantity=10
        )
        
        # Create cart
        self.cart = Cart.objects.create(user=self.user)
    
    def test_calculate_subtotal_empty_cart(self):
        """Test subtotal calculation for empty cart"""
        calculator = PriceCalculator(self.cart)
        subtotal = calculator.calculate_subtotal()
        
        self.assertEqual(subtotal, Decimal('0'))
    
    def test_calculate_subtotal_single_item(self):
        """Test subtotal calculation with single item"""
        CartItem.objects.create(
            cart=self.cart,
            product=self.product1,
            size='M',
            quantity=2
        )
        
        calculator = PriceCalculator(self.cart)
        subtotal = calculator.calculate_subtotal()
        
        # 100 * 2 = 200
        self.assertEqual(subtotal, Decimal('200.00'))
    
    def test_calculate_subtotal_multiple_items(self):
        """Test subtotal calculation with multiple items"""
        CartItem.objects.create(
            cart=self.cart,
            product=self.product1,
            size='M',
            quantity=2
        )
        CartItem.objects.create(
            cart=self.cart,
            product=self.product2,
            size='L',
            quantity=1
        )
        
        calculator = PriceCalculator(self.cart)
        subtotal = calculator.calculate_subtotal()
        
        # (100 * 2) + (200 * 1) = 400
        self.assertEqual(subtotal, Decimal('400.00'))
    
    def test_calculate_tax(self):
        """Test tax calculation (18% GST)"""
        CartItem.objects.create(
            cart=self.cart,
            product=self.product1,
            size='M',
            quantity=1
        )
        
        calculator = PriceCalculator(self.cart)
        tax = calculator.calculate_tax()
        
        # 100 * 0.18 = 18
        self.assertEqual(tax, Decimal('18.00'))
    
    def test_calculate_tax_with_subtotal(self):
        """Test tax calculation with provided subtotal"""
        calculator = PriceCalculator(self.cart)
        tax = calculator.calculate_tax(subtotal=Decimal('500.00'))
        
        # 500 * 0.18 = 90
        self.assertEqual(tax, Decimal('90.00'))
    
    def test_calculate_shipping_free_over_threshold(self):
        """Test free shipping for orders over 500"""
        CartItem.objects.create(
            cart=self.cart,
            product=self.product1,
            size='M',
            quantity=6  # 600 total
        )
        
        calculator = PriceCalculator(self.cart)
        shipping = calculator.calculate_shipping()
        
        self.assertEqual(shipping, Decimal('0'))
    
    def test_calculate_shipping_charged_under_threshold(self):
        """Test shipping charge for orders under 500"""
        CartItem.objects.create(
            cart=self.cart,
            product=self.product1,
            size='M',
            quantity=2  # 200 total
        )
        
        calculator = PriceCalculator(self.cart)
        shipping = calculator.calculate_shipping()
        
        self.assertEqual(shipping, Decimal('50'))
    
    def test_calculate_shipping_at_threshold(self):
        """Test shipping at exactly 500 threshold"""
        CartItem.objects.create(
            cart=self.cart,
            product=self.product1,
            size='M',
            quantity=5  # 500 total
        )
        
        calculator = PriceCalculator(self.cart)
        shipping = calculator.calculate_shipping()
        
        # At threshold, should be free
        self.assertEqual(shipping, Decimal('0'))
    
    def test_calculate_discount_no_coupon(self):
        """Test discount calculation without coupon"""
        calculator = PriceCalculator(self.cart)
        discount = calculator.calculate_discount()
        
        self.assertEqual(discount, Decimal('0'))
    
    def test_calculate_discount_with_coupon(self):
        """Test discount calculation with coupon"""
        calculator = PriceCalculator(
            self.cart,
            coupon_discount=Decimal('50.00')
        )
        discount = calculator.calculate_discount()
        
        self.assertEqual(discount, Decimal('50.00'))
    
    def test_calculate_total_without_discount(self):
        """Test total calculation without discount"""
        CartItem.objects.create(
            cart=self.cart,
            product=self.product1,
            size='M',
            quantity=2  # 200 subtotal
        )
        
        calculator = PriceCalculator(self.cart)
        total = calculator.calculate_total()
        
        # subtotal: 200
        # tax: 200 * 0.18 = 36
        # shipping: 50 (under 500)
        # total: 200 + 36 + 50 = 286
        self.assertEqual(total, Decimal('286.00'))
    
    def test_calculate_total_with_discount(self):
        """Test total calculation with discount"""
        CartItem.objects.create(
            cart=self.cart,
            product=self.product1,
            size='M',
            quantity=2  # 200 subtotal
        )
        
        calculator = PriceCalculator(
            self.cart,
            coupon_discount=Decimal('30.00')
        )
        total = calculator.calculate_total()
        
        # subtotal: 200
        # tax: 200 * 0.18 = 36
        # shipping: 50 (under 500)
        # discount: 30
        # total: 200 + 36 + 50 - 30 = 256
        self.assertEqual(total, Decimal('256.00'))
    
    def test_calculate_total_free_shipping(self):
        """Test total calculation with free shipping"""
        CartItem.objects.create(
            cart=self.cart,
            product=self.product1,
            size='M',
            quantity=6  # 600 subtotal
        )
        
        calculator = PriceCalculator(self.cart)
        total = calculator.calculate_total()
        
        # subtotal: 600
        # tax: 600 * 0.18 = 108
        # shipping: 0 (over 500)
        # total: 600 + 108 = 708
        self.assertEqual(total, Decimal('708.00'))
    
    def test_get_price_breakdown(self):
        """Test complete price breakdown"""
        CartItem.objects.create(
            cart=self.cart,
            product=self.product1,
            size='M',
            quantity=3  # 300 subtotal
        )
        
        calculator = PriceCalculator(
            self.cart,
            coupon_discount=Decimal('20.00')
        )
        breakdown = calculator.get_price_breakdown()
        
        self.assertEqual(breakdown['subtotal'], Decimal('300.00'))
        self.assertEqual(breakdown['tax'], Decimal('54.00'))  # 300 * 0.18
        self.assertEqual(breakdown['shipping'], Decimal('50.00'))  # under 500
        self.assertEqual(breakdown['discount'], Decimal('20.00'))
        self.assertEqual(breakdown['total'], Decimal('384.00'))  # 300 + 54 + 50 - 20
    
    def test_recalculate_clears_cache(self):
        """Test that recalculate clears cached values"""
        CartItem.objects.create(
            cart=self.cart,
            product=self.product1,
            size='M',
            quantity=1
        )
        
        calculator = PriceCalculator(self.cart)
        
        # Calculate initial total
        total1 = calculator.calculate_total()
        
        # Add another item
        CartItem.objects.create(
            cart=self.cart,
            product=self.product2,
            size='L',
            quantity=1
        )
        
        # Without recalculate, should return cached value
        total2 = calculator.calculate_total()
        self.assertEqual(total1, total2)
        
        # After recalculate, should return new value
        calculator.recalculate()
        total3 = calculator.calculate_total()
        self.assertNotEqual(total1, total3)
        self.assertGreater(total3, total1)
    
    def test_calculate_total_recalculates_within_one_second(self):
        """Test that price recalculation happens quickly (Requirement 14.5)"""
        import time
        
        CartItem.objects.create(
            cart=self.cart,
            product=self.product1,
            size='M',
            quantity=2
        )
        
        calculator = PriceCalculator(self.cart)
        
        # Measure calculation time
        start_time = time.time()
        calculator.calculate_total()
        end_time = time.time()
        
        calculation_time = end_time - start_time
        
        # Should complete within 1 second (Requirement 14.5)
        self.assertLess(calculation_time, 1.0)
