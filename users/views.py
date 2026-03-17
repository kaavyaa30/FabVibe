from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from .forms import (UserRegistrationForm, UserLoginForm, CustomPasswordResetForm, 
                    CustomSetPasswordForm, ProfileUpdateForm, AddressForm)
from .models import User, Address
from cart.utils import migrate_session_cart_to_user

def register(request):
    """User registration view with email/phone validation and OTP generation"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Save user with hashed password
            user = form.save()
            
            # Generate OTP
            otp_code = user.generate_otp()
            
            # Send OTP via email
            try:
                send_mail(
                    subject='FabVibe - Verify Your Account',
                    message=f'Your OTP code is: {otp_code}\n\nThis code will expire in 10 minutes.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(request, 'Registration successful! Please check your email for the OTP code.')
            except Exception as e:
                messages.warning(request, f'Registration successful! OTP: {otp_code} (Email sending failed)')
            
            # Send OTP via SMS if phone number provided
            if user.phone_number:
                try:
                    send_sms_otp(user.phone_number, otp_code)
                except Exception as e:
                    pass  # SMS is optional
            
            # Store user ID in session for OTP verification
            request.session['pending_user_id'] = user.id
            
            return redirect('users:verify_otp')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})


def send_sms_otp(phone_number, otp_code):
    """Send OTP via SMS (placeholder for SMS gateway integration)"""
    # This is a placeholder function for SMS integration
    # In production, integrate with Twilio or other SMS gateway
    if settings.SMS_BACKEND == 'console':
        print(f'SMS to {phone_number}: Your FabVibe OTP is {otp_code}')
    elif settings.SMS_BACKEND == 'twilio':
        # Twilio integration would go here
        pass

def login_view(request):
    """User login view supporting email or phone number"""
    if request.user.is_authenticated:
        return redirect('products:home')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Try to find user by email or phone number
            user = None
            try:
                # Check if username is email or phone
                if '@' in username:
                    user = User.objects.get(email=username)
                else:
                    user = User.objects.get(phone_number=username)
            except User.DoesNotExist:
                pass
            
            # Authenticate user
            if user:
                authenticated_user = authenticate(request, username=user.email, password=password)
                if authenticated_user:
                    # Migrate session cart BEFORE login (to preserve session key)
                    merged_count, total_items = migrate_session_cart_to_user(request, authenticated_user)
                    
                    # Now perform login
                    login(request, authenticated_user)
                    
                    # Show appropriate success message
                    if merged_count > 0:
                        messages.success(request, f'Login successful! {merged_count} item(s) from your cart have been restored.')
                    else:
                        messages.success(request, 'Login successful! Welcome back.')
                    
                    # Redirect to next page or home
                    next_url = request.GET.get('next', 'products:home')
                    return redirect(next_url)
            
            # Generic error message for security
            messages.error(request, 'Invalid credentials. Please try again.')
    else:
        form = UserLoginForm()
    
    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    """User logout view with session termination"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('products:home')

def verify_otp(request):
    """OTP verification view"""
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code')
        user_id = request.session.get('pending_user_id')
        
        if not user_id:
            messages.error(request, 'Session expired. Please register again.')
            return redirect('users:register')
        
        try:
            user = User.objects.get(id=user_id)
            
            # Verify OTP
            if user.otp_code == otp_code and user.is_otp_valid():
                # Mark email as verified
                user.email_verified = True
                user.otp_code = None
                user.otp_expiry = None
                user.save()
                
                # Clear session
                del request.session['pending_user_id']
                
                # Log the user in
                login(request, user)
                
                messages.success(request, 'Account verified successfully! Welcome to FabVibe.')
                return redirect('products:home')
            else:
                if not user.is_otp_valid():
                    messages.error(request, 'OTP has expired. Please request a new one.')
                else:
                    messages.error(request, 'Invalid OTP code. Please try again.')
        except User.DoesNotExist:
            messages.error(request, 'User not found. Please register again.')
            return redirect('users:register')
    
    return render(request, 'users/verify_otp.html')


def resend_otp(request):
    """Resend OTP to user"""
    user_id = request.session.get('pending_user_id')
    
    if not user_id:
        messages.error(request, 'Session expired. Please register again.')
        return redirect('users:register')
    
    try:
        user = User.objects.get(id=user_id)
        
        # Generate new OTP
        otp_code = user.generate_otp()
        
        # Send OTP via email
        try:
            send_mail(
                subject='FabVibe - Verify Your Account',
                message=f'Your new OTP code is: {otp_code}\n\nThis code will expire in 10 minutes.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            messages.success(request, 'New OTP sent to your email.')
        except Exception as e:
            messages.warning(request, f'New OTP: {otp_code} (Email sending failed)')
        
        # Send OTP via SMS if phone number provided
        if user.phone_number:
            try:
                send_sms_otp(user.phone_number, otp_code)
            except Exception as e:
                pass
        
        return redirect('users:verify_otp')
    except User.DoesNotExist:
        messages.error(request, 'User not found. Please register again.')
        return redirect('users:register')

@login_required
def profile(request):
    """User profile view with edit functionality"""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    # Get user's addresses
    addresses = request.user.addresses.all()
    
    context = {
        'form': form,
        'addresses': addresses,
    }
    return render(request, 'users/profile.html', context)

def password_reset_request(request):
    """Password reset request view - sends reset link to email"""
    if request.method == 'POST':
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            # Find user by email
            try:
                user = User.objects.get(email=email)
                
                # Generate password reset token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Build reset URL
                reset_url = request.build_absolute_uri(
                    f'/users/password-reset-confirm/{uid}/{token}/'
                )
                
                # Send email with reset link
                subject = 'FabVibe - Password Reset Request'
                message = f'''Hello {user.first_name},

You have requested to reset your password for your FabVibe account.

Click the link below to reset your password:
{reset_url}

This link will expire in 30 minutes.

If you did not request this password reset, please ignore this email.

Best regards,
FabVibe Team
'''
                
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    messages.success(request, 'Password reset link has been sent to your email.')
                except Exception as e:
                    messages.error(request, 'Failed to send email. Please try again later.')
                    return render(request, 'users/password_reset.html', {'form': form})
                
            except User.DoesNotExist:
                # Don't reveal if email exists or not for security
                messages.success(request, 'If an account exists with this email, a password reset link has been sent.')
            
            return redirect('users:login')
    else:
        form = CustomPasswordResetForm()
    
    return render(request, 'users/password_reset.html', {'form': form})


def password_reset_confirm(request, uidb64, token):
    """Password reset confirmation view - validates token and updates password"""
    try:
        # Decode user ID
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    # Validate token (30-minute expiry is built into Django's token generator)
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = CustomSetPasswordForm(user, request.POST)
            if form.is_valid():
                # Save new password
                form.save()
                messages.success(request, 'Your password has been reset successfully. You can now log in with your new password.')
                return redirect('users:login')
        else:
            form = CustomSetPasswordForm(user)
        
        return render(request, 'users/password_reset_confirm.html', {
            'form': form,
            'validlink': True
        })
    else:
        # Invalid or expired token
        messages.error(request, 'This password reset link is invalid or has expired. Please request a new one.')
        return render(request, 'users/password_reset_confirm.html', {
            'validlink': False
        })


@login_required
def add_address(request):
    """Add new shipping address"""
    next_url = request.GET.get('next', '') or request.POST.get('next', '')
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            if address.is_default:
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
            address.save()
            messages.success(request, 'Address added successfully!')
            if next_url == 'checkout':
                return redirect('orders:checkout')
            return redirect('users:profile')
    else:
        form = AddressForm()

    return render(request, 'users/address_form.html', {'form': form, 'action': 'Add', 'next': next_url})


@login_required
def edit_address(request, address_id):
    """Edit existing shipping address"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    next_url = request.GET.get('next', '') or request.POST.get('next', '')

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            updated_address = form.save(commit=False)
            if updated_address.is_default:
                Address.objects.filter(user=request.user, is_default=True).exclude(id=address_id).update(is_default=False)
            updated_address.save()
            messages.success(request, 'Address updated successfully!')
            if next_url == 'checkout':
                return redirect('orders:checkout')
            return redirect('users:profile')
    else:
        form = AddressForm(instance=address)

    return render(request, 'users/address_form.html', {'form': form, 'action': 'Edit', 'address': address, 'next': next_url})


@login_required
def delete_address(request, address_id):
    """Delete shipping address"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    next_url = request.GET.get('next', '') or request.POST.get('next', '')

    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted successfully!')
        if next_url == 'checkout':
            return redirect('orders:checkout')
        return redirect('users:profile')

    return render(request, 'users/address_confirm_delete.html', {'address': address, 'next': next_url})
