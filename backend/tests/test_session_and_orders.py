import sys
import tempfile
import time
import unittest
import os
from pathlib import Path
from unittest import mock

from fastapi.security import HTTPAuthorizationCredentials

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import api_auth
import reply_server
from db_manager import DBManager
from routes import auth_routes, order_routes
from fastapi.testclient import TestClient


class SessionAndOrderTests(unittest.TestCase):
    def test_login_verify_logout_flow_via_api(self):
        client = TestClient(reply_server.app)
        session_store = {}
        fake_user = {
            "id": 7,
            "username": "tester",
            "email": "tester@example.com",
            "nickname": "Tester",
            "is_admin": False,
            "is_active": True,
            "created_at": None,
            "updated_at": None,
        }

        def save_auth_session(token_hash, user_id, expires_at):
            session_store[token_hash] = {
                "id": len(session_store) + 1,
                "user_id": user_id,
                "expires_at": expires_at,
            }
            return True

        def get_auth_session(token_hash):
            return session_store.get(token_hash)

        def delete_auth_session(token_hash):
            session_store.pop(token_hash, None)
            return True

        with mock.patch.object(reply_server.cookie_manager, "manager", mock.Mock()), mock.patch.object(
            auth_routes.db_manager,
            "verify_user_password",
            side_effect=lambda username, password: username == "tester" and password == "secret",
        ), mock.patch.object(
            auth_routes.db_manager,
            "get_user_by_username",
            side_effect=lambda username: fake_user if username == "tester" else None,
        ), mock.patch.object(
            api_auth.db_manager,
            "save_auth_session",
            side_effect=save_auth_session,
        ), mock.patch.object(
            api_auth.db_manager,
            "get_auth_session",
            side_effect=get_auth_session,
        ), mock.patch.object(
            api_auth.db_manager,
            "delete_auth_session",
            side_effect=delete_auth_session,
        ), mock.patch.object(
            api_auth.db_manager,
            "get_user_by_id",
            side_effect=lambda user_id: fake_user if user_id == fake_user["id"] else None,
        ):
            login_response = client.post("/login", json={"username": "tester", "password": "secret"})
            self.assertEqual(login_response.status_code, 200)
            login_body = login_response.json()
            self.assertTrue(login_body["success"])
            self.assertTrue(login_body["token"])

            headers = {"Authorization": f"Bearer {login_body['token']}"}
            verify_response = client.get("/verify", headers=headers)
            self.assertEqual(verify_response.status_code, 200)
            self.assertEqual(
                verify_response.json(),
                {
                    "authenticated": True,
                    "user_id": 7,
                    "username": "tester",
                    "is_admin": False,
                },
            )

            logout_response = client.post("/logout", headers=headers)
            self.assertEqual(logout_response.status_code, 200)
            self.assertEqual(logout_response.json(), {"message": "已登出"})

            verify_after_logout = client.get("/verify", headers=headers)
            self.assertEqual(verify_after_logout.status_code, 200)
            self.assertEqual(verify_after_logout.json(), {"authenticated": False})

    def test_health_endpoint_returns_503_when_dependency_unhealthy(self):
        client = TestClient(reply_server.app)

        with mock.patch.object(reply_server.cookie_manager, "manager", None), mock.patch.object(
            reply_server.db_manager,
            "get_all_cookies",
            return_value={},
        ):
            response = client.get("/health")

        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertIn("detail", body)
        self.assertEqual(body["detail"]["status"], "unhealthy")

    def test_auth_session_crud_with_sqlite(self):
        with mock.patch.dict(os.environ, {"DATABASE_URL": "", "DATABASE_URL_XIANYU": ""}):
            with tempfile.TemporaryDirectory() as temp_dir:
                manager = DBManager(str(Path(temp_dir) / "auth_sessions.db"))
                self.assertTrue(manager.create_user("alice", "alice@example.com", "secret"))

                user = manager.get_user_by_username("alice")
                self.assertIsNotNone(user)

                token_hash = "token-hash-1"
                expires_at = time.time() + 60

                self.assertTrue(manager.save_auth_session(token_hash, user["id"], expires_at))

                session = manager.get_auth_session(token_hash)
                self.assertIsNotNone(session)
                self.assertEqual(session["user_id"], user["id"])
                self.assertEqual(float(session["expires_at"]), expires_at)

                self.assertTrue(manager.delete_auth_session(token_hash))
                self.assertIsNone(manager.get_auth_session(token_hash))
                manager.close()

    def test_verify_token_reads_database_session(self):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="plain-token")

        with mock.patch.object(
            api_auth.db_manager,
            "get_auth_session",
            return_value={"id": 9, "user_id": 3, "expires_at": time.time() + 60},
        ), mock.patch.object(
            api_auth.db_manager,
            "get_user_by_id",
            return_value={
                "id": 3,
                "username": "tester",
                "email": "tester@example.com",
                "nickname": "Tester",
                "is_admin": True,
                "is_active": True,
                "created_at": None,
                "updated_at": None,
            },
        ), mock.patch.object(api_auth.db_manager, "delete_auth_session") as delete_mock:
            user_info = api_auth.verify_token(credentials)

        self.assertIsNotNone(user_info)
        self.assertEqual(user_info["username"], "tester")
        self.assertEqual(user_info["user_id"], 3)
        self.assertTrue(user_info["is_admin"])
        delete_mock.assert_not_called()

    def test_get_user_orders_limits_cookie_scope(self):
        calls = {}

        class FakeDBManager:
            @staticmethod
            def get_all_cookies(user_id):
                self.assertEqual(user_id, 12)
                return {"cookie-a": "value-a", "cookie-b": "value-b"}

            @staticmethod
            def get_orders_page_by_cookie_ids(cookie_ids, status, keyword, page, page_size):
                calls["cookie_ids"] = cookie_ids
                calls["status"] = status
                calls["keyword"] = keyword
                calls["page"] = page
                calls["page_size"] = page_size
                return ([{"order_id": "o-1", "cookie_id": "cookie-b"}], 1)

        with mock.patch.object(order_routes, "db_manager", FakeDBManager()):
            result = order_routes.get_user_orders(
                cookie_id="cookie-b",
                status="paid",
                keyword="Buyer",
                page=2,
                page_size=5,
                current_user={"user_id": 12, "username": "tester", "is_admin": False},
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["total_pages"], 1)
        self.assertEqual(
            calls,
            {
                "cookie_ids": ["cookie-b"],
                "status": "paid",
                "keyword": "buyer",
                "page": 2,
                "page_size": 5,
            },
        )


if __name__ == "__main__":
    unittest.main()
