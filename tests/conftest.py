"""Shared fixtures: in-memory SQLite app + client for fast, isolated tests."""
import os
from unittest.mock import patch

import pytest
from peewee import SqliteDatabase

from app.database import db
from app.models.product import Product
from app.models.user import User

TEST_DB = SqliteDatabase(":memory:")
MODELS = [Product, User]


def _test_init_db(app):
    """Replace the real Postgres init_db with one that uses our in-memory SQLite."""
    db.initialize(TEST_DB)

    @app.before_request
    def _db_connect():
        db.connect(reuse_if_open=True)

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    """Bind all models to an in-memory SQLite DB, create tables, and clean up after each test."""
    TEST_DB.bind(MODELS)
    TEST_DB.connect()
    TEST_DB.create_tables(MODELS)
    yield
    TEST_DB.drop_tables(MODELS)
    TEST_DB.close()


@pytest.fixture()
def app():
    """Create a Flask app wired to the in-memory test DB."""
    with patch("app.init_db", _test_init_db), patch("app.init_cache"):
        from app import create_app
        application = create_app()
        application.config["TESTING"] = True
        return application


@pytest.fixture()
def client(app):
    with app.app_context():
        yield app.test_client()


@pytest.fixture()
def sample_product():
    """Insert and return a single product for tests that need existing data."""
    return Product.create(
        name="Test Widget",
        category="Electronics",
        description="A test product",
        price=29.99,
        stock=100,
    )


@pytest.fixture()
def sample_products():
    """Insert and return 5 products for list tests."""
    products = []
    for i in range(1, 6):
        products.append(
            Product.create(
                name=f"Product {i}",
                category="Books" if i % 2 else "Electronics",
                description=f"Description {i}",
                price=i * 10.0,
                stock=i * 5,
            )
        )
    return products

@pytest.fixture()
def sample_user():
    """Insert and return a single user for tests that need existing data."""
    return User.create(
        email="fixture@example.com",
        username="fixture_user",
    )
 
 
@pytest.fixture()
def sample_users():
    """Insert and return 20 users — enough for pagination tests (per_page=10)
    and for delete tests that target a fixed ID like /users/200 via seed data."""
    users = []
    for i in range(1, 21):
        users.append(
            User.create(
                email=f"user{i}@example.com",
                username=f"testuser_{i}",
            )
        )
    return users