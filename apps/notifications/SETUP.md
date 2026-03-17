# Kaagjee — Notifications App Setup

## 1. Install dependency

```bash
pip install firebase-admin
```

## 2. Firebase credentials lao

Firebase Console → Project Settings → Service Accounts
→ **Generate new private key** → `firebase-credentials.json` save karo project root mein
→ `.gitignore` mein add karo!

## 3. settings.py mein add karo

```python
INSTALLED_APPS = [
    ...
    'apps.notifications',   # ← add
]

# Firebase credentials
FIREBASE_CREDENTIALS_PATH = BASE_DIR / 'firebase-credentials.json'
```

## 4. main urls.py mein add karo

```python
path('api/notifications/', include('apps.notifications.urls')),
```

## 5. Files copy karo

| Is file ko | Yahan rakho |
|------------|-------------|
| `__init__.py` | `apps/notifications/__init__.py` |
| `apps.py` | `apps/notifications/apps.py` |
| `models.py` | `apps/notifications/models.py` |
| `firebase.py` | `apps/notifications/firebase.py` |
| `signals.py` | `apps/notifications/signals.py` |
| `serializers.py` | `apps/notifications/serializers.py` |
| `views.py` | `apps/notifications/views.py` |
| `urls.py` | `apps/notifications/urls.py` |
| `admin.py` | `apps/notifications/admin.py` |
| `migrations/__init__.py` | `apps/notifications/migrations/__init__.py` |
| `migrations/0001_initial.py` | `apps/notifications/migrations/0001_initial.py` (**replace old file**) |
| `orders_migration_0003.py` | `apps/orders/migrations/0003_order_note.py` |
| `PASTE_INTO_orders_models.py` | `apps/orders/models.py` ke **end mein paste** karo |

## 6. Migrate karo

```bash
python manage.py migrate notifications
python manage.py migrate orders
```

---

## API Reference

### User APIs (JWT token required)

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/notifications/register-token/` | FCM token register karo |
| DELETE | `/api/notifications/remove-token/` | Token remove karo (logout pe call karo) |
| GET | `/api/notifications/` | Apni saari notifications |
| GET | `/api/notifications/unread-count/` | Unread count |
| POST | `/api/notifications/<pk>/mark-read/` | Ek notification read karo |
| POST | `/api/notifications/mark-all-read/` | Saari read karo |

### Admin APIs (is_staff=True required)

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/notifications/admin/` | Admin notifications |
| GET | `/api/notifications/admin/unread-count/` | Admin unread count |
| POST | `/api/notifications/admin/<pk>/mark-read/` | Mark read |
| POST | `/api/notifications/admin/mark-all-read/` | Mark all read |
| POST | `/api/notifications/admin/orders/<id>/add-note/` | Order pe note add karo |
| GET | `/api/notifications/admin/orders/<id>/notes/` | Order ke notes dekho |
| POST | `/api/notifications/admin/send/` | Kisi bhi user ko custom push |

### Register Token Example (frontend)

```javascript
// On app start / Firebase token refresh
await fetch('/api/notifications/register-token/', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${jwtToken}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ token: firebaseToken, platform: 'web' })
})

// On logout
await fetch('/api/notifications/remove-token/', {
  method: 'DELETE',
  headers: { 'Authorization': `Bearer ${jwtToken}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ token: firebaseToken })
})
```

### Add Order Note (admin)

```http
POST /api/notifications/admin/orders/KJ-20250313-ABC12/add-note/
Authorization: Bearer <admin_jwt>

{
  "note": "Aapke documents verify ho gaye hain.",
  "is_internal": false,
  "notify_user": true
}
```

`is_internal: true` → sirf admin dekhega, user ko push nahi jaayegi.

---

## Auto-notifications (signals se automatic)

| Event | User ko | Admin ko |
|-------|---------|----------|
| New order | ✅ Order Placed | ✅ New Order |
| Order → Processing | ✅ | ❌ |
| Order → Completed | ✅ | ❌ |
| Order → Cancelled | ✅ | ❌ |
| Payment success | ✅ | ✅ |
| Payment failed | ✅ | ✅ |
| Admin adds note | ✅ (if notify_user=True) | ❌ |
