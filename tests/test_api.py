"""Integration tests — hit the API via Flask test client."""
import json
import io

class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}


class TestListProducts:
    def test_empty_list(self, client):
        resp = client.get("/products")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_list_returns_products(self, client, sample_products):
        resp = client.get("/products")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 5

    def test_list_product_fields(self, client, sample_product):
        resp = client.get("/products")
        data = resp.get_json()
        product = data[0]
        assert "id" in product
        assert "name" in product
        assert "category" in product
        assert "price" in product
        assert "stock" in product


class TestGetProduct:
    def test_get_existing_product(self, client, sample_product):
        resp = client.get(f"/products/{sample_product.id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "Test Widget"
        assert data["category"] == "Electronics"

    def test_get_nonexistent_product(self, client):
        resp = client.get("/products/99999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data


class TestCreateProduct:
    def test_create_valid_product(self, client):
        payload = {
            "name": "New Widget",
            "category": "Electronics",
            "price": 19.99,
            "stock": 50,
        }
        resp = client.post("/products", json=payload)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "New Widget"
        assert data["id"] is not None

    def test_create_product_with_description(self, client):
        payload = {
            "name": "Described Widget",
            "category": "Tools",
            "description": "A great tool",
            "price": 9.99,
            "stock": 10,
        }
        resp = client.post("/products", json=payload)
        assert resp.status_code == 201
        assert resp.get_json()["description"] == "A great tool"

    def test_create_product_missing_name(self, client):
        payload = {"category": "Electronics", "price": 10, "stock": 5}
        resp = client.post("/products", json=payload)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "validation failed"
        assert any("name" in d for d in data["details"])

    def test_create_product_missing_multiple_fields(self, client):
        resp = client.post("/products", json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert len(data["details"]) >= 4

    def test_create_product_negative_price(self, client):
        payload = {"name": "Bad", "category": "X", "price": -5, "stock": 1}
        resp = client.post("/products", json=payload)
        assert resp.status_code == 400
        assert any("price" in d for d in resp.get_json()["details"])

    def test_create_product_negative_stock(self, client):
        payload = {"name": "Bad", "category": "X", "price": 5, "stock": -1}
        resp = client.post("/products", json=payload)
        assert resp.status_code == 400
        assert any("stock" in d for d in resp.get_json()["details"])

    def test_create_product_invalid_price_type(self, client):
        payload = {"name": "Bad", "category": "X", "price": "free", "stock": 1}
        resp = client.post("/products", json=payload)
        assert resp.status_code == 400

    def test_create_product_empty_name(self, client):
        payload = {"name": "  ", "category": "X", "price": 5, "stock": 1}
        resp = client.post("/products", json=payload)
        assert resp.status_code == 400

    def test_create_product_no_json_body(self, client):
        resp = client.post("/products", data="not json", content_type="text/plain")
        assert resp.status_code == 400

    def test_create_product_strips_whitespace(self, client):
        payload = {"name": "  Padded  ", "category": "  Books  ", "price": 5, "stock": 1}
        resp = client.post("/products", json=payload)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Padded"
        assert data["category"] == "Books"


    def test_create_product_name_too_long(self, client):
        payload = {"name": "A" * 256, "category": "X", "price": 5, "stock": 1}
        resp = client.post("/products", json=payload)
        assert resp.status_code == 400
        assert any("255" in d for d in resp.get_json()["details"])

    def test_create_product_category_too_long(self, client):
        payload = {"name": "OK", "category": "B" * 256, "price": 5, "stock": 1}
        resp = client.post("/products", json=payload)
        assert resp.status_code == 400
        assert any("255" in d for d in resp.get_json()["details"])

    def test_create_product_duplicate_name(self, client, sample_product):
        payload = {
            "name": "Test Widget",
            "category": "Electronics",
            "price": 5,
            "stock": 1,
        }
        resp = client.post("/products", json=payload)
        assert resp.status_code == 409
        assert "already exists" in resp.get_json()["error"]


class TestReadiness:
    def test_readiness_returns_checks(self, client):
        resp = client.get("/health/ready")
        data = resp.get_json()
        assert "checks" in data
        assert "status" in data


class TestErrorHandlers:
    def test_404_unknown_route(self, client):
        resp = client.get("/nonexistent")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "not found"

    def test_405_wrong_method(self, client):
        resp = client.delete("/products")
        assert resp.status_code == 405
        data = resp.get_json()
        assert data["error"] == "method not allowed"

    def test_405_patch_on_product(self, client, sample_product):
        resp = client.patch(f"/products/{sample_product.id}")
        assert resp.status_code == 405


class TestLoadUsersCSV:
    def test_load_users_csv(self, client):
        """POST /users/bulk with a CSV file uploads 400 rows successfully."""
        csv_content = "email,username\n"
        for i in range(400):
            csv_content += f"user{i}@example.com,user{i}\n"
 
        data = {
            "file": (io.BytesIO(csv_content.encode()), "users.csv"),
            "row_count": 400,
        }
        resp = client.post(
            "/users/bulk",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code in (200, 201)
        body = resp.get_json()
        assert body is not None
 
 
class TestGetUsersList:
    def test_get_users_list(self, client, sample_users):
        """GET /users returns 200 with a non-empty list."""
        resp = client.get("/users")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
 
    def test_get_users_pagination(self, client, sample_users):
        """GET /users?page=1&per_page=10 returns exactly 10 items."""
        resp = client.get("/users", query_string={"page": 1, "per_page": 10})
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 10
 
    def test_get_users_list_fields(self, client, sample_users):
        """Each user in the list exposes expected fields."""
        resp = client.get("/users")
        assert resp.status_code == 200
        user = resp.get_json()[0]
        assert "id" in user
        assert "email" in user
        assert "username" in user
 
 
class TestGetUserById:
    def test_get_user_by_id(self, client, sample_user):
        """GET /users/<id> returns the correct user."""
        resp = client.get(f"/users/{sample_user.id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == sample_user.id
 
    def test_get_nonexistent_user(self, client):
        """GET /users/99999 returns 404 with an error key."""
        resp = client.get("/users/99999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data
 
 
class TestCreateUser:
    def test_create_user(self, client):
        """POST /users with valid payload returns 201 and echoes submitted fields."""
        payload = {
            "email": "testuser_create@example.com",
            "username": "testuser_create",
        }
        resp = client.post("/users", json=payload)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["email"] == payload["email"]
        assert data["username"] == payload["username"]
        assert data.get("id") is not None
 
    def test_create_user_missing_email(self, client):
        """POST /users without email returns 400."""
        resp = client.post("/users", json={"username": "noemail"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
 
    def test_create_user_missing_username(self, client):
        """POST /users without username returns 400."""
        resp = client.post("/users", json={"email": "nousername@example.com"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
 
    def test_create_user_duplicate_email(self, client, sample_user):
        """POST /users with a duplicate email returns 409."""
        payload = {"email": sample_user.email, "username": "different_username"}
        resp = client.post("/users", json=payload)
        assert resp.status_code == 409
 
    def test_create_user_no_json_body(self, client):
        """POST /users with non-JSON body returns 400."""
        resp = client.post("/users", data="not json", content_type="text/plain")
        assert resp.status_code == 400
 
 
class TestUpdateUser:
    def test_update_user(self, client, sample_user):
        """PUT /users/<id> with a new username returns 200 and updated value."""
        resp = client.put(
            f"/users/{sample_user.id}",
            json={"username": "updated_username"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["username"] == "updated_username"
 
    def test_update_nonexistent_user(self, client):
        """PUT /users/99999 returns 404."""
        resp = client.put("/users/99999", json={"username": "ghost"})
        assert resp.status_code == 404
        assert "error" in resp.get_json()
 
    def test_update_user_no_body(self, client, sample_user):
        """PUT /users/<id> with empty body returns 400."""
        resp = client.put(f"/users/{sample_user.id}", json={})
        assert resp.status_code == 400
 
 
class TestDeleteUser:
    def test_delete_user(self, client, sample_users):
        """DELETE an existing user returns 200 or 204."""
        user_id = sample_users[-1].id
        resp = client.delete(f"/users/{user_id}")
        assert resp.status_code in (200, 204)

    def test_delete_nonexistent_user(self, client):
        """DELETE /users/99999 returns 404."""
        resp = client.delete("/users/99999")
        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_delete_user_twice(self, client, sample_user):
        """Deleting the same user twice returns 404 on the second attempt."""
        user_id = sample_user.id
        client.delete(f"/users/{user_id}")
        resp = client.delete(f"/users/{user_id}")
        assert resp.status_code == 404