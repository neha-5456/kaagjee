"""
CloudServices India - Account Serializers
"""
from rest_framework import serializers
from .models import User, OTP, UserAddress


class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    purpose = serializers.ChoiceField(choices=OTP.Purpose.choices)


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp_code = serializers.CharField(max_length=6)
    purpose = serializers.ChoiceField(choices=OTP.Purpose.choices)


class RegisterRequestSerializer(serializers.Serializer):
    """Serializer for registration request - sends OTP"""
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=15)

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class RegisterVerifySerializer(serializers.Serializer):
    """Serializer for OTP verification during registration"""
    phone_number = serializers.CharField(max_length=15)
    otp_code = serializers.CharField(max_length=6)

    def validate(self, data):
        phone = data.get('phone_number')
        otp_code = data.get('otp_code')
        
        # Check if OTP exists and is valid
        try:
            otp = OTP.objects.filter(
                phone_number=phone,
                purpose=OTP.Purpose.REGISTRATION,
                is_verified=False
            ).latest('created_at')
        except OTP.DoesNotExist:
            raise serializers.ValidationError({'otp_code': 'Invalid or expired OTP. Please request a new one.'})
        
        if not otp.is_valid(otp_code):
            otp.attempts += 1
            otp.save()
            if otp.attempts >= 3:
                raise serializers.ValidationError({'otp_code': 'Too many invalid attempts. Please request a new OTP.'})
            raise serializers.ValidationError({'otp_code': f'Invalid OTP. {3 - otp.attempts} attempts remaining.'})
        
        # Double-check user doesn't exist
        if User.objects.filter(phone_number=phone).exists():
            raise serializers.ValidationError({'phone_number': 'User already exists with this phone number.'})
        
        data['otp_instance'] = otp
        return data


class LoginRequestSerializer(serializers.Serializer):
    """Serializer for login request - sends OTP"""
    phone_number = serializers.CharField(max_length=15)

    def validate_phone_number(self, value):
        if not User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("No account found with this phone number. Please register first.")
        return value


class LoginVerifySerializer(serializers.Serializer):
    """Serializer for OTP verification during login"""
    phone_number = serializers.CharField(max_length=15)
    otp_code = serializers.CharField(max_length=6)

    def validate(self, data):
        phone = data.get('phone_number')
        otp_code = data.get('otp_code')
        
        # Check if user exists
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            raise serializers.ValidationError({'phone_number': 'No account found with this phone number. Please register first.'})
        
        # Check if OTP exists and is valid
        try:
            otp = OTP.objects.filter(
                phone_number=phone,
                purpose=OTP.Purpose.LOGIN,
                is_verified=False
            ).latest('created_at')
        except OTP.DoesNotExist:
            raise serializers.ValidationError({'otp_code': 'Invalid or expired OTP. Please request a new one.'})
        
        if not otp.is_valid(otp_code):
            otp.attempts += 1
            otp.save()
            if otp.attempts >= 3:
                raise serializers.ValidationError({'otp_code': 'Too many invalid attempts. Please request a new OTP.'})
            raise serializers.ValidationError({'otp_code': f'Invalid OTP. {3 - otp.attempts} attempts remaining.'})
        
        data['user'] = user
        data['otp_instance'] = otp
        return data





class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'email', 'first_name', 'last_name', 'avatar', 'role', 'is_verified', 'date_joined']
        read_only_fields = ['id', 'phone_number', 'role', 'is_verified', 'date_joined']


class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = '__all__'
        read_only_fields = ['user']
