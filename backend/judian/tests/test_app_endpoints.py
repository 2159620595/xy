import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

import backend.judian.judian_backend.__init__ as judian_backend
from backend.judian.judian_backend.__init__ import app, get_current_user


class VerifyEndpointTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_current_user] = lambda: {
            "username": "tester",
            "is_admin": True,
        }
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_verify_returns_authenticated_payload(self):
        response = self.client.get("/verify")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "authenticated": True,
                "username": "tester",
                "is_admin": True,
            },
        )


class PublicBatchPreviewEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch(
        "backend.judian.judian_backend.__init__.build_public_batch_purchase_preview",
        return_value={"count": 2, "requiredDiamond": 20},
    )
    @patch(
        "backend.judian.judian_backend.__init__.get_public_unlock_session_or_404",
        return_value=(object(), object(), object()),
    )
    def test_batch_preview_wraps_preview_payload(self, unlock_mock, preview_mock):
        response = self.client.get(
            "/public/unlock/session-1/batch/preview",
            params={"count": 2, "vip_id": "vip-1", "package_type": "month"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "success": True,
                "preview": {"count": 2, "requiredDiamond": 20},
            },
        )
        unlock_mock.assert_called_once()
        preview_mock.assert_called_once()


class PublicVipPlansFallbackTests(unittest.TestCase):
    def setUp(self):
        judian_backend._PUBLIC_VIP_PLANS_CACHE = []
        judian_backend._PUBLIC_VIP_PLANS_CACHE_AT = 0.0
        judian_backend._PUBLIC_WEB_CLIENT_RECEIVE_PEM = ''

    def build_encrypted_payload(self, payload: dict) -> str:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        aes_key = "R5xThLNmXbpDOgyj"
        aes_iv = aes_key[::-1].encode()
        encrypted_key = public_key.encrypt(aes_key.encode(), rsa_padding.PKCS1v15())
        padder = PKCS7(128).padder()
        padded_payload = padder.update(judian_backend.json.dumps(payload).encode()) + padder.finalize()
        cipher = Cipher(algorithms.AES(aes_key.encode()), modes.CBC(aes_iv))
        encryptor = cipher.encryptor()
        encrypted_body = encryptor.update(padded_payload) + encryptor.finalize()
        return private_pem, (
            f"{judian_backend.base64.b64encode(encrypted_key).decode()}."
            f"{judian_backend.base64.b64encode(encrypted_body).decode()}"
        )

    @patch("backend.judian.judian_backend.__init__.get_batch_script_path", return_value="Z:/missing-test-vip.js")
    @patch("backend.judian.judian_backend.__init__.build_public_web_headers", return_value={})
    def test_remote_get_public_vip_plans_decrypts_http_fallback_payload(self, _headers_mock, _script_path_mock):
        private_pem, encrypted_text = self.build_encrypted_payload(
            {
                "code": 20000,
                "data": [
                    {"id": 8, "title": "1天 VIP", "coin": 5},
                    {"id": 9, "title": "7天 VIP", "coin": 20},
                ],
            }
        )

        class FakeResponse:
            status_code = 200

            def __init__(self, text: str):
                self.text = text

            def raise_for_status(self):
                return None

            def json(self):
                raise ValueError("not json")

        class FakeSession:
            def __init__(self):
                self.headers = {}

            def get(self, url, timeout=None):
                return FakeResponse(encrypted_text)

        with patch(
            "backend.judian.judian_backend.__init__.get_public_web_client_receive_pem",
            return_value=private_pem,
        ), patch(
            "backend.judian.judian_backend.__init__.requests.Session",
            return_value=FakeSession(),
        ):
            plans = judian_backend.remote_get_public_vip_plans(timeout=1)

        self.assertEqual(
            plans,
            [
                {"id": 8, "title": "1天 VIP", "coin": 5},
                {"id": 9, "title": "7天 VIP", "coin": 20},
            ],
        )
