from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from users.models import User


class UserModelTest(TestCase):
    """Test cases for the User model"""
    
    def test_create_user_with_email(self):
        """Test creating a user with email"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertFalse(user.email_verified)
        self.assertFalse(user.phone_verified)
        self.assertIsNone(user.otp_code)
        self.assertIsNone(user.otp_expiry)
    
    def test_create_user_with_phone(self):
        """Test creating a user with phone number"""
        user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123',
            phone_number='+1234567890'
        )
        self.assertEqual(user.phone_number, '+1234567890')
        self.assertFalse(user.phone_verified)
    
    def test_phone_number_validation(self):
        """Test phone number format validation"""
        user = User(
            username='testuser3',
            email='test3@example.com',
            phone_number='invalid'
        )
        with self.assertRaises(ValidationError):
            user.full_clean()
    
    def test_email_unique_constraint(self):
        """Test that email must be unique"""
        User.objects.create_user(
            username='user1',
            email='duplicate@example.com',
            password='testpass123'
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
                username='user2',
                email='duplicate@example.com',
                password='testpass123'
            )
    
    def test_phone_unique_constraint(self):
        """Test that phone number must be unique"""
        User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='testpass123',
            phone_number='+9876543210'
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
                username='user4',
                email='user4@example.com',
                password='testpass123',
                phone_number='+9876543210'
            )
    
    def test_generate_otp(self):
        """Test OTP generation"""
        user = User.objects.create_user(
            username='testuser5',
            email='test5@example.com',
            password='testpass123'
        )
        otp = user.generate_otp()
        
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())
        self.assertEqual(user.otp_code, otp)
        self.assertIsNotNone(user.otp_expiry)
        self.assertTrue(user.is_otp_valid())
    
    def test_otp_expiry(self):
        """Test OTP expiry validation"""
        user = User.objects.create_user(
            username='testuser6',
            email='test6@example.com',
            password='testpass123'
        )
        user.otp_code = '123456'
        user.otp_expiry = timezone.now() - timezone.timedelta(minutes=1)
        user.save()
        
        self.assertFalse(user.is_otp_valid())
    
    def test_email_verified_field(self):
        """Test email_verified field"""
        user = User.objects.create_user(
            username='testuser7',
            email='test7@example.com',
            password='testpass123'
        )
        self.assertFalse(user.email_verified)
        
        user.email_verified = True
        user.save()
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
    
    def test_phone_verified_field(self):
        """Test phone_verified field"""
        user = User.objects.create_user(
            username='testuser8',
            email='test8@example.com',
            password='testpass123',
            phone_number='+1234567890'
        )
        self.assertFalse(user.phone_verified)
        
        user.phone_verified = True
        user.save()
        user.refresh_from_db()
        self.assertTrue(user.phone_verified)
