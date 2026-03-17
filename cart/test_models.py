from django.test import TestCase
from django.contrib.auth import get_user_model
from cart.models import Cart, CartItem, Coupon
from products.models import Product, Category
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class CartModelTest(TestCase):
    """Test Cart model"""
    
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
    
    def test_cart_creation_with_user(self):
        """Test creating a cart for authenticated user"""
        cart = Cart.objects.create(user=self.user)
        self.assertEqual(cart.user, self.user)
        self.assertIsNone(cart.session_key)
        self.assertIsNotNone(cart.created_at)
        self.assertIsNotNone(cart.updated_at)
    
    def test_cart_creation_with_session(self):
        """Test creating a cart for guest user with session key"""
        cart = Cart.objects.create(session_key='test_session_123')
        self.assertIsNone(cart.user)
        self.assertEqual(cart.session_key, 'test_session_123')
    
    def test_cart_str_with_user(self):
        """Test cart string representation with user"""
        cart = Cart.objects.create(user=self.user)
        self.assertEqual(str(cart), f"Cart for {self.user.email}")
    
    def test_cart_str_with_session(self):
        """Test cart string representation with session"""
        cart = Cart.objects.create(session_key='test_session_123')
        self.assertEqual(str(cart), "Cart for session test_session_123")
    
    def test_cart_get_total(self):
        """Test cart total calculation"""
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            size='M',
            quantity=2
        )
        expected_total = self.product.price * 2
        self.assertEqual(cart.get_total(), expected_total)


class CartItemModelTest(TestCase):
    """Test CartItem model"""
    
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
        self.cart = Cart.objects.create(user=self.user)
    
    def test_cart_item_creation(self):
        """Test creating a cart item"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            size='M',
            quantity=2
        )
        self.assertEqual(cart_item.cart, self.cart)
        self.assertEqual(cart_item.product, self.product)
        self.assertEqual(cart_item.size, 'M')
        self.assertEqual(cart_item.quantity, 2)
    
    def test_cart_item_str(self):
        """Test cart item string representation"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            size='M',
            quantity=2
        )
        self.assertEqual(str(cart_item), f"2 x {self.product.name}")
    
    def test_cart_item_get_subtotal(self):
        """Test cart item subtotal calculation"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            size='M',
            quantity=3
        )
        expected_subtotal = self.product.price * 3
        self.assertEqual(cart_item.get_subtotal(), expected_subtotal)
    
    def test_cart_item_unique_constraint(self):
        """Test unique constraint on cart, product, and size"""
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            size='M',
            quantity=1
        )
        # Attempting to create duplicate should raise error
        with self.assertRaises(Exception):
            CartItem.objects.create(
                cart=self.cart,
                product=self.product,
                size='M',
                quantity=1
            )


class CouponModelTest(TestCase):
    """Test Coupon model"""
    
    def setUp(self):
        self.valid_from = timezone.now()
        self.valid_to = timezone.now() + timedelta(days=7)
    
    def test_coupon_creation(self):
        """Test creating a coupon"""
        coupon = Coupon.objects.create(
            code='SAVE10',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_purchase_amount=Decimal('50.00'),
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            is_active=True
        )
        self.assertEqual(coupon.code, 'SAVE10')
        self.assertEqual(coupon.discount_type, 'percentage')
        self.assertEqual(coupon.discount_value, Decimal('10.00'))
    
    def test_coupon_str(self):
        """Test coupon string representation"""
        coupon = Coupon.objects.create(
            code='SAVE10',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            valid_from=self.valid_from,
            valid_to=self.valid_to
        )
        self.assertEqual(str(coupon), 'SAVE10')
    
    def test_coupon_is_valid(self):
        """Test coupon validity check"""
        coupon = Coupon.objects.create(
            code='SAVE10',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            is_active=True
        )
        self.assertTrue(coupon.is_valid())
    
    def test_coupon_is_invalid_when_inactive(self):
        """Test coupon is invalid when inactive"""
        coupon = Coupon.objects.create(
            code='SAVE10',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            is_active=False
        )
        self.assertFalse(coupon.is_valid())
    
    def test_coupon_is_invalid_when_expired(self):
        """Test coupon is invalid when expired"""
        coupon = Coupon.objects.create(
            code='SAVE10',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            valid_from=timezone.now() - timedelta(days=10),
            valid_to=timezone.now() - timedelta(days=1),
            is_active=True
        )
        self.assertFalse(coupon.is_valid())
    
    def test_coupon_usage_limit(self):
        """Test coupon usage limit"""
        coupon = Coupon.objects.create(
            code='SAVE10',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            is_active=True,
            usage_limit=5,
            used_count=5
        )
        self.assertFalse(coupon.is_valid())
