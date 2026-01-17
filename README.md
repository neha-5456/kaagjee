# 🚀 CloudServices India

**Pan-India Digital Services Platform**

A complete Django-based backend with Visual Form Builder for non-technical admins.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 📝 **Visual Form Builder** | Drag-drop form creation - no JSON knowledge needed |
| 🗺️ **State-City Filter** | Dependent dropdown - cities filter by state |
| ✍️ **Rich Text Editor** | Beautiful description with formatting |
| 📱 **Phone OTP Auth** | Indian phone number login |
| 💰 **Razorpay Integration** | Full & 50% advance payments |
| 🇮🇳 **Hindi Labels** | Admin interface in Hindi for non-technical users |

---

## 📁 Project Structure

```
cloudservices/
└── backend/
    ├── manage.py
    ├── requirements.txt
    ├── core/
    │   ├── settings.py
    │   └── urls.py
    ├── apps/
    │   ├── accounts/      # User Auth (OTP)
    │   ├── locations/     # States & Cities
    │   ├── categories/    # Categories
    │   ├── products/      # Products + Form Builder
    │   ├── orders/        # Orders & Form Submissions
    │   └── payments/      # Razorpay Payments
    └── templates/
        └── admin/
            └── products/
                └── product/
                    └── change_form.html  # Visual Form Builder
```

---

## 🔧 Installation

### Step 1: Extract & Navigate
```cmd
cd E:\kaagjee\backend
```

### Step 2: Create Virtual Environment
```cmd
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```cmd
pip install -r requirements.txt
```

### Step 4: Create Directories
```cmd
mkdir static media
```

### Step 5: Run Migrations
```cmd
python manage.py makemigrations
python manage.py migrate
```

### Step 6: Create Superuser
```cmd
python manage.py createsuperuser
```
Enter: Phone number (e.g., +919999999999), Password

### Step 7: Run Server
```cmd
python manage.py runserver
```

---

## 🌐 URLs

| URL | Description |
|-----|-------------|
| http://127.0.0.1:8000/admin/ | Django Admin Dashboard |
| http://127.0.0.1:8000/api/docs/ | API Documentation (Swagger) |

---

## 📝 Using Visual Form Builder

1. **Go to Admin** → Products → Add Product
2. **Scroll to "Form Builder" section**
3. **Click field types** to add (Text, Email, Phone, File, etc.)
4. **Click on added field** to edit settings (label, required, etc.)
5. **Save the product** - form schema saves automatically!

### Available Field Types:
- Text, Long Text, Email, Phone, Number
- Date, Dropdown, Checkbox, Radio
- File Upload, Image Upload
- Aadhar, PAN, Pincode

---

## 🗺️ State-City Filter

When adding/editing a product:
1. Select **States** in "Available States"
2. **Cities dropdown automatically filters** to show only cities from selected states

---

## 📡 API Endpoints

### Authentication
```
POST /api/v1/auth/send-otp/     - Send OTP
POST /api/v1/auth/verify-otp/   - Verify OTP
POST /api/v1/auth/register/     - Register
POST /api/v1/auth/login/        - Login with OTP
GET  /api/v1/auth/profile/      - Get Profile
```

### Products
```
GET  /api/v1/products/                    - List Products
GET  /api/v1/products/featured/           - Featured Products
GET  /api/v1/products/{slug}/             - Product Detail
GET  /api/v1/products/{slug}/form-schema/ - Get Form Schema
```

### Orders
```
POST /api/v1/orders/create/      - Create Order
GET  /api/v1/orders/             - List Orders
GET  /api/v1/orders/{id}/        - Order Detail
```

### Payments
```
POST /api/v1/payments/initiate/  - Initiate Payment
POST /api/v1/payments/verify/    - Verify Payment
GET  /api/v1/payments/           - List Payments
```

---

## ⚙️ Configuration

### Environment Variables (Optional)
Create `.env` file:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
RAZORPAY_KEY_ID=rzp_test_xxx
RAZORPAY_KEY_SECRET=xxx
```

---

## 🛠️ Tech Stack

- **Backend:** Django 5.x, Django REST Framework
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Auth:** JWT + Phone OTP
- **Payments:** Razorpay
- **Rich Text:** Quill.js
- **Icons:** Font Awesome 6

---

## 📞 Support

For issues, check Django Admin or API docs at `/api/docs/`

---

Made with ❤️ for Indian Digital Services
