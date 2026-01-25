"""
CloudServices India - User & Authentication Models
===================================================
Features:
- Phone number based authentication
- OTP verification
- User roles (Admin, Staff, Customer)
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
import random
import string


class UserManager(BaseUserManager):
    """Custom user manager for phone-based authentication"""
    
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('Phone number is required')
        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User Model with Phone Number as Username"""
    
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        STAFF = 'staff', 'Staff'
        CUSTOMER = 'customer', 'Customer'

    # Primary Fields
    phone_number = PhoneNumberField(unique=True, verbose_name='Phone Number')
    email = models.EmailField(unique=True, null=True, blank=True)
    
    # Profile
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    # Role & Status
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False, verbose_name='Phone Verified')
    
    # Timestamps
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else str(self.phone_number)


class OTP(models.Model):
    """OTP Model for Phone Verification"""
    
    class Purpose(models.TextChoices):
        REGISTRATION = 'registration', 'Registration'
        LOGIN = 'login', 'Login'
        RESET_PASSWORD = 'reset_password', 'Reset Password'

    phone_number = PhoneNumberField()
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'OTP'
        verbose_name_plural = 'OTPs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.phone_number} - {self.purpose}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self, code):
        if self.is_expired():
            return False
        if self.is_verified:
            return False
        if self.attempts >= 3:
            return False
        return self.otp_code == code

    @classmethod
    def generate(cls, phone_number, purpose):
        """Generate new OTP and invalidate old ones"""
        from django.conf import settings
        
        # Delete old unverified OTPs
        cls.objects.filter(phone_number=phone_number, purpose=purpose, is_verified=False).delete()
        
        # Generate 6-digit OTP
        otp_code = ''.join(random.choices(string.digits, k=6))
        
        # Set expiry
        expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 5)
        expires_at = timezone.now() + timezone.timedelta(minutes=expiry_minutes)
        
        return cls.objects.create(
            phone_number=phone_number,
            otp_code=otp_code,
            purpose=purpose,
            expires_at=expires_at
        )


class UserAddress(models.Model):
    """User Address Model"""
    
    class AddressType(models.TextChoices):
        HOME = 'home', 'Home'
        OFFICE = 'office', 'Office'
        OTHER = 'other', 'Other'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=20, choices=AddressType.choices, default=AddressType.HOME)
    
    full_name = models.CharField(max_length=200)
    phone = PhoneNumberField()
    address_line_1 = models.CharField(max_length=500)
    address_line_2 = models.CharField(max_length=500, blank=True)
    landmark = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.city}"

    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default:
            UserAddress.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
