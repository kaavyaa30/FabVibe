from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from cart.models import Cart, CartItem, Coupon
from products.models import Product, Category, Inventory

User = get_user_model()


class CouponApplicationTest(TestCase):
    """Test coupon application functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='1234567890',
            password='testpass123'
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
        
        # Create valid coupon
        now = timezone.now()
        self.valid_coupon = Coupon.objects.create(
            code='SAVE10',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_purchase_amount=Decimal('0.00'),
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            is_active=True
        )
        
        # Login user
        self.client.login(email='test@example.com', password='testpass123')
    
    def test_apply_valid_coupon(self):
        """Test applying a valid coupon code"""
        response = self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': 'SAVE10'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['coupon_code'], 'SAVE10')
        self.assertEqual(Decimal(str(data['discount'])), Decimal('20.00'))  # 10% of 200
        
        # Final total should include tax and shipping
        # Subtotal: 200, Tax: 36 (18%), Shipping: 50, Discount: 20
        # Total: 200 + 36 + 50 - 20 = 266
        self.assertEqual(Decimal(str(data['final_total'])), Decimal('266.00'))
        
        # Check session
        self.assertEqual(self.client.session['coupon_code'], 'SAVE10')
        self.assertEqual(Decimal(str(self.client.session['coupon_discount'])), Decimal('20.00'))
    
    def test_apply_invalid_coupon(self):
        """Test applying an invalid coupon code"""
        response = self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': 'INVALID'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Invalid coupon code', data['error'])
    
    def test_apply_expired_coupon(self):
        """Test applying an expired coupon"""
        now = timezone.now()
        expired_coupon = Coupon.objects.create(
            code='EXPIRED',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_purchase_amount=Decimal('0.00'),
            valid_from=now - timedelta(days=30),
            valid_to=now - timedelta(days=1),
            is_active=True
        )
        
        response = self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': 'EXPIRED'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('expired', data['error'].lower())
    
    def test_apply_inactive_coupon(self):
        """Test applying an inactive coupon"""
        now = timezone.now()
        inactive_coupon = Coupon.objects.create(
            code='INACTIVE',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_purchase_amount=Decimal('0.00'),
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            is_active=False
        )
        
        response = self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': 'INACTIVE'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('no longer active', data['error'])
    
    def test_apply_coupon_below_minimum_purchase(self):
        """Test applying coupon when cart total is below minimum"""
        now = timezone.now()
        min_coupon = Coupon.objects.create(
            code='MIN500',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_purchase_amount=Decimal('500.00'),
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            is_active=True
        )
        
        response = self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': 'MIN500'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Minimum purchase amount', data['error'])
    
    def test_apply_fixed_discount_coupon(self):
        """Test applying a fixed amount discount coupon"""
        now = timezone.now()
        fixed_coupon = Coupon.objects.create(
            code='FIXED20',
            discount_type='fixed',
            discount_value=Decimal('20.00'),
            min_purchase_amount=Decimal('0.00'),
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            is_active=True
        )
        
        response = self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': 'FIXED20'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(Decimal(str(data['discount'])), Decimal('20.00'))
        
        # Final total should include tax and shipping
        # Subtotal: 200, Tax: 36 (18%), Shipping: 50, Discount: 20
        # Total: 200 + 36 + 50 - 20 = 266
        self.assertEqual(Decimal(str(data['final_total'])), Decimal('266.00'))
    
    def test_apply_percentage_coupon_with_max_discount(self):
        """Test percentage coupon with maximum discount cap"""
        now = timezone.now()
        capped_coupon = Coupon.objects.create(
            code='CAPPED',
            discount_type='percentage',
            discount_value=Decimal('50.00'),  # 50% would be $100
            min_purchase_amount=Decimal('0.00'),
            max_discount_amount=Decimal('30.00'),  # But capped at $30
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            is_active=True
        )
        
        response = self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': 'CAPPED'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(Decimal(str(data['discount'])), Decimal('30.00'))  # Capped at 30
    
    def test_enforce_one_coupon_per_order(self):
        """Test that only one coupon can be applied at a time"""
        # Apply first coupon
        self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': 'SAVE10'}),
            content_type='application/json'
        )
        
        # Try to apply second coupon
        now = timezone.now()
        second_coupon = Coupon.objects.create(
            code='SAVE20',
            discount_type='percentage',
            discount_value=Decimal('20.00'),
            min_purchase_amount=Decimal('0.00'),
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            is_active=True
        )
        
        response = self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': 'SAVE20'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('already applied', data['error'])
    
    def test_remove_coupon(self):
        """Test removing an applied coupon"""
        # Apply coupon first
        self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': 'SAVE10'}),
            content_type='application/json'
        )
        
        # Remove coupon
        response = self.client.post(
            reverse('cart:remove_coupon'),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(Decimal(str(data['cart_total'])), Decimal('200.00'))
        
        # Check session
        self.assertNotIn('coupon_code', self.client.session)
        self.assertNotIn('coupon_discount', self.client.session)
    
    def test_remove_coupon_when_none_applied(self):
        """Test removing coupon when none is applied"""
        response = self.client.post(
            reverse('cart:remove_coupon'),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('No coupon applied', data['error'])
    
    def test_coupon_code_case_insensitive(self):
        """Test that coupon codes are case-insensitive"""
        response = self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': 'save10'}),  # lowercase
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_empty_coupon_code(self):
        """Test applying empty coupon code"""
        response = self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': ''}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('enter a coupon code', data['error'])
    
    def test_coupon_usage_limit(self):
        """Test coupon with usage limit"""
        now = timezone.now()
        limited_coupon = Coupon.objects.create(
            code='LIMITED',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_purchase_amount=Decimal('0.00'),
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            is_active=True,
            usage_limit=1,
            used_count=1  # Already used once
        )
        
        response = self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': 'LIMITED'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('usage limit', data['error'])
    
    def test_cart_detail_displays_coupon(self):
        """Test that cart detail page displays applied coupon"""
        # Apply coupon
        self.client.post(
            reverse('cart:apply_coupon'),
            data=json.dumps({'code': 'SAVE10'}),
            content_type='application/json'
        )
        
        # Get cart detail page
        response = self.client.get(reverse('cart:cart_detail'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SAVE10')
        self.assertContains(response, 'Discount:')
        self.assertIn('coupon_code', response.context)
        self.assertIn('coupon_discount', response.context)
        self.assertIn('final_total', response.context)


class CouponModelTest(TestCase):
    """Test Coupon model validation"""
    
    def test_coupon_is_valid_method(self):
        """Test the is_valid method of Coupon model"""
        now = timezone.now()
        coupon = Coupon.objects.create(
            code='TEST',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_purchase_amount=Decimal('0.00'),
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            is_active=True
        )
        
        self.assertTrue(coupon.is_valid())
    
    def test_coupon_invalid_when_inactive(self):
        """Test coupon is invalid when inactive"""
        now = timezone.now()
        coupon = Coupon.objects.create(
            code='TEST',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_purchase_amount=Decimal('0.00'),
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            is_active=False
        )
        
        self.assertFalse(coupon.is_valid())
    
    def test_coupon_invalid_when_expired(self):
        """Test coupon is invalid when expired"""
        now = timezone.now()
        coupon = Coupon.objects.create(
            code='TEST',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_purchase_amount=Decimal('0.00'),
            valid_from=now - timedelta(days=30),
            valid_to=now - timedelta(days=1),
            is_active=True
        )
        
        self.assertFalse(coupon.is_valid())
    
    def test_coupon_invalid_when_not_yet_valid(self):
        """Test coupon is invalid when not yet valid"""
        now = timezone.now()
        coupon = Coupon.objects.create(
            code='TEST',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_purchase_amount=Decimal('0.00'),
            valid_from=now + timedelta(days=1),
            valid_to=now + timedelta(days=30),
            is_active=True
        )
        
        self.assertFalse(coupon.is_valid())
    
    def test_coupon_invalid_when_usage_limit_reached(self):
        """Test coupon is invalid when usage limit is reached"""
        now = timezone.now()
        coupon = Coupon.objects.create(
            code='TEST',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_purchase_amount=Decimal('0.00'),
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            is_active=True,
            usage_limit=5,
            used_count=5
        )
        
        self.assertFalse(coupon.is_valid())
