"""
AgroTrack AI — Firebase Admin SDK Integration
Manages server-side Firebase Admin authentication, service account initialization,
and cloud resource connectivity.
"""

import os
import logging
from typing import Optional
import firebase_admin
from firebase_admin import credentials, auth, db

logger = logging.getLogger("agrotrack.firebase")

# Path to the service account credentials JSON
DEFAULT_KEY_PATH = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY", DEFAULT_KEY_PATH)

_firebase_app: Optional[firebase_admin.App] = None


def initialize_firebase(key_path: Optional[str] = None) -> Optional[firebase_admin.App]:
    """
    Initializes the Firebase Admin SDK using the service account certificate.
    Safe against multiple/redundant initialization attempts.
    """
    global _firebase_app
    if _firebase_app is not None or firebase_admin._apps:
        try:
            _firebase_app = firebase_admin.get_app()
            return _firebase_app
        except ValueError:
            pass

    target_path = key_path or SERVICE_ACCOUNT_PATH
    if os.path.exists(target_path):
        try:
            cred = credentials.Certificate(target_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully for project: %s", _firebase_app.project_id)
            print(f"[+] Firebase Admin SDK initialized for project '{_firebase_app.project_id}'")
            return _firebase_app
        except Exception as e:
            logger.warning("Failed to initialize Firebase Admin SDK from '%s': %s", target_path, e)
            print(f"[!] Warning: Could not initialize Firebase Admin SDK: {e}")
            return None
    else:
        logger.info("Firebase service account key not found at '%s'. Running in local mock mode.", target_path)
        return None


def get_firebase_app() -> Optional[firebase_admin.App]:
    """Returns the initialized Firebase Admin App or attempts initialization."""
    if not firebase_admin._apps:
        return initialize_firebase()
    return firebase_admin.get_app()
