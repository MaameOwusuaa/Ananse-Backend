import unittest
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.services.naa import build_site_context


class AdminApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_secret = settings.secret_key
        settings.secret_key = "test-secret-for-admin-api"
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.session_factory = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(bind=cls.engine)

        def override_get_db():
            db = cls.session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.router.on_startup.clear()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()
        settings.secret_key = cls.original_secret

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        with self.session_factory() as db:
            admin = models.User(
                full_name="ANANSE Admin",
                email="admin@example.com",
                password_hash="not-used",
                role="admin",
            )
            visitor = models.User(
                full_name="Ama Visitor",
                email="ama@example.com",
                password_hash="not-used",
                role="visitor",
            )
            site = models.Site(
                slug="cape-coast-castle",
                name="Cape Coast Castle",
                region="Central",
                category="Forts and castles",
                latitude=5.1,
                longitude=-1.2,
                summary="A reviewed heritage site summary.",
                history=[],
                facts={},
                accessibility=[],
            )
            db.add_all([admin, visitor, site])
            db.commit()
            db.refresh(admin)
            db.refresh(visitor)
            db.refresh(site)
            db.add(models.Visit(user_id=visitor.id, site_id=site.id, source="app"))
            db.commit()
            self.admin_token = create_access_token(admin.email)
            self.visitor_token = create_access_token(visitor.email)

    def test_plans_are_private_to_visitor_and_visible_to_admin(self):
        payload = {
            "site_slug": "cape-coast-castle",
            "visit_date": (date.today() + timedelta(days=2)).isoformat(),
            "visit_time": "10:30",
            "visitors": "3",
        }
        visitor_headers = {"Authorization": f"Bearer {self.visitor_token}"}
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

        created = self.client.post("/api/plans", json=payload, headers=visitor_headers)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["userEmail"], "ama@example.com")

        own_plans = self.client.get("/api/plans/mine", headers=visitor_headers)
        self.assertEqual(own_plans.status_code, 200)
        self.assertEqual(len(own_plans.json()), 1)
        self.assertEqual(self.client.get("/api/plans/mine", headers={"Authorization": f"Bearer {self.admin_token}"}).json(), [])

        forbidden = self.client.get("/api/plans/admin", headers=visitor_headers)
        self.assertEqual(forbidden.status_code, 403)

        admin_plans = self.client.get("/api/plans/admin", headers=admin_headers)
        self.assertEqual(admin_plans.status_code, 200)
        self.assertEqual(admin_plans.json()[0]["siteName"], "Cape Coast Castle")

        users = self.client.get("/api/admin/users", headers=admin_headers)
        self.assertEqual(users.status_code, 200)
        visitor = next(user for user in users.json() if user["email"] == "ama@example.com")
        self.assertEqual(visitor["fullName"], "Ama Visitor")
        self.assertEqual(visitor["visitCount"], 1)
        self.assertEqual(visitor["planCount"], 1)
        self.assertNotIn("password_hash", visitor)

        denied_users = self.client.get("/api/admin/users", headers=visitor_headers)
        self.assertEqual(denied_users.status_code, 403)

        site = self.client.get("/api/sites/cape-coast-castle").json()
        edited = self.client.put(
            f"/api/sites/id/{site['id']}",
            headers=admin_headers,
            json={
                "history": ["Admin-reviewed trail story."],
                "facts": {
                    "Naa reference notes": "Ask permission before photographing people.",
                    "ananseTrailV1": '{"introduction":"Updated route context."}',
                },
            },
        )
        self.assertEqual(edited.status_code, 200)
        with self.session_factory() as db:
            context = build_site_context(db, "cape-coast-castle")
        self.assertIn("Admin-reviewed trail story.", context)
        self.assertIn("Ask permission before photographing people.", context)


if __name__ == "__main__":
    unittest.main()
