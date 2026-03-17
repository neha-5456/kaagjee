"""
Firebase Cloud Messaging helpers
----------------------------------
Install:
    pip install firebase-admin

settings.py mein add karo (KISI EK option choose karo):

    # Option A — JSON file (local dev)
    FIREBASE_CREDENTIALS_PATH = BASE_DIR / 'firebase-credentials.json'

    # Option B — env variable (production)
    import json, os
    FIREBASE_CREDENTIALS = json.loads(os.environ['FIREBASE_CREDENTIALS_JSON'])

Credentials kaise milenge:
    Firebase Console → Project Settings → Service Accounts
    → Generate new private key → save as firebase-credentials.json
    → .gitignore mein daalo!
"""
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)
_app = None


def _init():
    """Singleton Firebase app initializer."""
    global _app
    if _app is not None:
        return _app
    try:
        import firebase_admin
        from firebase_admin import credentials
        # Already initialized by someone else?
        try:
            _app = firebase_admin.get_app()
            return _app
        except ValueError:
            pass

        cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
        cred_dict = getattr(settings, 'FIREBASE_CREDENTIALS', None)

        if cred_dict:
            cred = credentials.Certificate(cred_dict)
        elif cred_path:
            cred = credentials.Certificate(str(cred_path))
        else:
            logger.error(
                'Firebase: credentials not configured. '
                'Set FIREBASE_CREDENTIALS_PATH or FIREBASE_CREDENTIALS in settings.py'
            )
            return None

        _app = firebase_admin.initialize_app(cred)
        logger.info('Firebase: initialized ✓')
        return _app

    except ImportError:
        logger.error('Firebase: firebase-admin not installed → pip install firebase-admin')
        return None
    except Exception as exc:
        logger.error(f'Firebase: init error — {exc}')
        return None


# ─────────────────────────────────────────────────────────────
# LOW-LEVEL SEND
# ─────────────────────────────────────────────────────────────

def _build_message_kwargs(title: str, body: str, data: dict):
    """Common Android + APNS config."""
    from firebase_admin import messaging
    return dict(
        notification=messaging.Notification(title=title, body=body),
        data={str(k): str(v) for k, v in (data or {}).items()},
        android=messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                sound='default',
                click_action='FLUTTER_NOTIFICATION_CLICK',
            ),
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound='default', badge=1)
            )
        ),
    )


def send_to_token(token: str, title: str, body: str, data: dict = None) -> bool:
    """Send to a single FCM token. Returns True on success."""
    if not _init():
        return False
    try:
        from firebase_admin import messaging
        msg = messaging.Message(token=token, **_build_message_kwargs(title, body, data))
        resp = messaging.send(msg)
        logger.debug(f'Firebase: sent → {resp}')
        return True
    except Exception as exc:
        logger.warning(f'Firebase: send_to_token failed — {exc}')
        return False


def send_multicast(tokens: list, title: str, body: str, data: dict = None) -> dict:
    """
    Send to multiple tokens at once.
    Returns {'success': N, 'failure': N, 'invalid_tokens': [...]}
    """
    if not tokens or not _init():
        return {'success': 0, 'failure': 0, 'invalid_tokens': []}
    try:
        from firebase_admin import messaging
        msg = messaging.MulticastMessage(
            tokens=tokens,
            **_build_message_kwargs(title, body, data)
        )
        resp = messaging.send_each_for_multicast(msg)

        invalid = []
        for idx, r in enumerate(resp.responses):
            if not r.success:
                code = getattr(getattr(r, 'exception', None), 'code', '')
                if code in ('registration-token-not-registered', 'invalid-registration-token'):
                    invalid.append(tokens[idx])

        result = {'success': resp.success_count, 'failure': resp.failure_count, 'invalid_tokens': invalid}
        logger.info(f'Firebase: multicast {result}')
        return result
    except Exception as exc:
        logger.error(f'Firebase: send_multicast error — {exc}')
        return {'success': 0, 'failure': len(tokens), 'invalid_tokens': []}


def _deactivate(invalid_tokens: list):
    if not invalid_tokens:
        return
    from .models import FCMDevice
    n = FCMDevice.objects.filter(token__in=invalid_tokens).update(is_active=False)
    logger.info(f'Firebase: deactivated {n} invalid tokens')


# ─────────────────────────────────────────────────────────────
# HIGH-LEVEL HELPERS  (used by signals + views)
# ─────────────────────────────────────────────────────────────

def push_to_user(user, title: str, body: str, data: dict = None, notif_obj=None):
    """
    Push to all active FCM devices of a user.
    Pass notif_obj (UserNotification) to auto-mark push_sent=True.
    """
    from .models import FCMDevice
    tokens = list(FCMDevice.objects.filter(user=user, is_active=True).values_list('token', flat=True))
    if not tokens:
        return
    result = send_multicast(tokens, title, body, data)
    _deactivate(result['invalid_tokens'])
    if notif_obj and result['success'] > 0:
        notif_obj.push_sent    = True
        notif_obj.push_sent_at = timezone.now()
        notif_obj.save(update_fields=['push_sent', 'push_sent_at'])


def push_to_admins(title: str, body: str, data: dict = None, notif_obj=None):
    """
    Push to all active FCM devices of admin/staff users.
    Pass notif_obj (AdminNotification) to auto-mark push_sent=True.
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    from .models import FCMDevice

    User = get_user_model()
    admin_ids = User.objects.filter(
        is_active=True
    ).filter(
        Q(is_staff=True) | Q(role='admin') | Q(role='staff')
    ).values_list('id', flat=True)

    tokens = list(FCMDevice.objects.filter(user_id__in=admin_ids, is_active=True).values_list('token', flat=True))
    if not tokens:
        return
    result = send_multicast(tokens, title, body, data)
    _deactivate(result['invalid_tokens'])
    if notif_obj and result['success'] > 0:
        notif_obj.push_sent    = True
        notif_obj.push_sent_at = timezone.now()
        notif_obj.save(update_fields=['push_sent', 'push_sent_at'])
