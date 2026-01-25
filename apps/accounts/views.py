"""
CloudServices India - Account Views
"""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .models import User, OTP, UserAddress
from .serializers import (
    RegisterRequestSerializer, RegisterVerifySerializer,
    LoginRequestSerializer, LoginVerifySerializer,
    UserSerializer, UserAddressSerializer
)


class RegisterRequestView(APIView):
    """Step 1: Register request - Check user existence and send OTP"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        
        # Debug: Print registration data to check if it's being stored
        registration_data = {
            'first_name': serializer.validated_data.get('first_name', ''),
            'last_name': serializer.validated_data.get('last_name', ''),
            'email': serializer.validated_data.get('email', '')
        }
        print(f"Storing registration data: {registration_data}")
        
        # Store registration data in session for temporary storage
        request.session[f'registration_data_{phone_number}'] = registration_data
        
        # Generate and send OTP
        otp = OTP.generate(phone_number, OTP.Purpose.REGISTRATION)
        
        return Response({
            'success': True,
            'message': 'OTP sent successfully to your phone number',
            'data': {
                'phone_number': str(phone_number),
                'expires_in_minutes': 5,
                # Remove this in production!
                'otp_code_dev_only': otp.otp_code
            }
        }, status=status.HTTP_200_OK)


class RegisterVerifyView(APIView):
    """Step 2: Verify OTP and complete registration"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Verification failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark OTP as verified
        otp = serializer.validated_data['otp_instance']
        otp.is_verified = True
        otp.save()
        
        # Get registration data from session
        phone_number = serializer.validated_data['phone_number']
        registration_data = request.session.get(f'registration_data_{phone_number}', {})
        
        # Debug: Print retrieved data
        print(f"Retrieved registration data: {registration_data}")
        
        # Create user with stored registration data
        user_data = {
            'phone_number': phone_number,
            'first_name': registration_data.get('first_name', ''),
            'last_name': registration_data.get('last_name', ''),
            'email': registration_data.get('email', ''),
            'is_verified': True,
            'is_active': True
        }
        
        # Debug: Print user data before creation
        print(f"Creating user with data: {user_data}")
        
        user = User.objects.create_user(**user_data)
        
        # Clean up session data
        request.session.pop(f'registration_data_{phone_number}', None)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'Registration completed successfully. You are now logged in.',
            'data': {
                'user': {
                    'id': user.id,
                    'phone_number': str(user.phone_number),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': user.full_name,
                    'is_verified': user.is_verified,
                    'date_joined': user.date_joined.isoformat()
                },
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }
        }, status=status.HTTP_201_CREATED)


class LoginRequestView(APIView):
    """Step 1: Login request - Check user existence and send OTP"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        
        # Generate and send OTP
        otp = OTP.generate(phone_number, OTP.Purpose.LOGIN)
        
        # In production, send SMS here
        # For development, include OTP in response (remove in production)
        
        return Response({
            'success': True,
            'message': 'OTP sent successfully to your registered phone number',
            'data': {
                'phone_number': str(phone_number),
                'expires_in_minutes': 5,
                # Remove this in production!
                'otp_code_dev_only': otp.otp_code
            }
        }, status=status.HTTP_200_OK)


class LoginVerifyView(APIView):
    """Step 2: Verify OTP and complete login"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Login failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark OTP as verified
        otp = serializer.validated_data['otp_instance']
        otp.is_verified = True
        otp.save()
        
        # Get user and update last login
        user = serializer.validated_data['user']
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'Login successful. Welcome back!',
            'data': {
                'user': {
                    'id': user.id,
                    'phone_number': str(user.phone_number),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': user.full_name,
                    'is_verified': user.is_verified,
                    'last_login': user.last_login.isoformat() if user.last_login else None
                },
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }
        }, status=status.HTTP_200_OK)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get/Update user profile"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class AddressListCreateView(generics.ListCreateAPIView):
    """List/Create user addresses"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserAddressSerializer

    def get_queryset(self):
        return UserAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get/Update/Delete user address"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserAddressSerializer

    def get_queryset(self):
        return UserAddress.objects.filter(user=self.request.user)
