# Kaagjee Orders & Payment System

Complete order management with Razorpay payment integration supporting full and half (50%) payment options.

## 🔄 Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER FLOW                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. LOGIN USER                                                           │
│       ↓                                                                  │
│  2. VIEW PRODUCT → Fill Form → SUBMIT                                    │
│       ↓                                                                  │
│  3. FORM SUBMISSION created → AUTO ADD TO CART                          │
│       ↓                                                                  │
│  4. CART PAGE → Select Payment Type (Full/Half)                         │
│       ↓                                                                  │
│  5. CHECKOUT → CREATE ORDER → RAZORPAY PAYMENT                          │
│       ↓                                                                  │
│  6A. FULL PAYMENT → Order Complete                                       │
│       OR                                                                 │
│  6B. HALF PAYMENT → Pay 50% → Order Partial Paid                        │
│       ↓                                                                  │
│  7. MY ORDERS → View Pending Payment → PAY REMAINING                    │
│       ↓                                                                  │
│  8. Order Fully Paid ✓                                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

### Step 1: Copy orders app
```bash
cp -r orders/ your_project/
```

### Step 2: Install Razorpay
```bash
pip install razorpay
```

### Step 3: Add to settings.py
```python
INSTALLED_APPS = [
    ...
    'orders',
]

# Razorpay Configuration
RAZORPAY_KEY_ID = 'rzp_test_xxxxxxxxxx'
RAZORPAY_KEY_SECRET = 'your_secret_key'
```

### Step 4: Add URLs
```python
# urls.py
urlpatterns = [
    ...
    path('api/orders/', include('orders.urls')),
]
```

### Step 5: Run Migrations
```bash
python manage.py makemigrations orders
python manage.py migrate
```

---

## 🔗 API Endpoints

### Form Submission
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/orders/submit-form/` | Submit form & add to cart |
| POST | `/api/orders/submit-form-files/` | Submit with file uploads |
| GET | `/api/orders/my-submissions/` | Get user's submissions |

### Cart
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orders/cart/` | Get cart |
| GET | `/api/orders/cart/count/` | Cart count |
| DELETE | `/api/orders/cart/item/<id>/remove/` | Remove item |
| DELETE | `/api/orders/cart/clear/` | Clear cart |

### Checkout & Payment
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/orders/checkout/` | Create order & Razorpay order |
| POST | `/api/orders/verify-payment/` | Verify Razorpay payment |

### Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orders/my-orders/` | Get user's orders |
| GET | `/api/orders/pending-payments/` | Orders with pending payment |
| GET | `/api/orders/<order_id>/` | Order detail |
| POST | `/api/orders/<order_id>/pay-pending/` | Pay remaining amount |

---

## 📝 API Examples

### 1. Submit Product Form
```javascript
POST /api/orders/submit-form/
{
    "product_id": 1,
    "form_data": {
        "full_name": "Rahul Kumar",
        "phone": "9876543210",
        "aadhar_number": "1234-5678-9012"
    }
}
```

### 2. Checkout (Select Payment Type)
```javascript
POST /api/orders/checkout/
{
    "payment_type": "half",  // or "full"
    "user_name": "Rahul Kumar",
    "user_email": "rahul@example.com",
    "user_phone": "9876543210"
}

// Response includes Razorpay order details
{
    "success": true,
    "data": {
        "order": {...},
        "payment": {
            "amount": 499.00,
            "razorpay_order_id": "order_xxx",
            "razorpay_key": "rzp_test_xxx"
        }
    }
}
```

### 3. Verify Payment (After Razorpay)
```javascript
POST /api/orders/verify-payment/
{
    "razorpay_order_id": "order_xxx",
    "razorpay_payment_id": "pay_xxx",
    "razorpay_signature": "signature_xxx"
}
```

### 4. Pay Pending Amount
```javascript
POST /api/orders/KJ-20260122-12345/pay-pending/
// Returns new Razorpay order for remaining amount
```

---

## 🎨 Frontend Razorpay Integration

```javascript
// After checkout API call
const options = {
    key: paymentData.razorpay_key,
    amount: paymentData.amount * 100,
    currency: 'INR',
    name: 'Kaagjee',
    order_id: paymentData.razorpay_order_id,
    handler: async function(response) {
        // Verify payment
        await fetch('/api/orders/verify-payment/', {
            method: 'POST',
            body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature
            })
        });
    },
    prefill: {
        name: paymentData.user_name,
        email: paymentData.user_email,
        contact: paymentData.user_phone
    }
};

const rzp = new Razorpay(options);
rzp.open();
```

---

## 📊 Order Statuses

| Status | Description |
|--------|-------------|
| `pending` | Payment not started |
| `partial_paid` | 50% paid |
| `paid` | Fully paid |
| `processing` | Being processed |
| `completed` | Completed |
| `cancelled` | Cancelled |

---

## 🔐 Test Credentials

```
Card: 4111 1111 1111 1111
Expiry: Any future date
CVV: Any 3 digits
```
