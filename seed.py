"""Create tables and seed the database with 100 sample products."""
import random

from dotenv import load_dotenv

load_dotenv()

from app.database import db, init_db
from app.models.product import Product
from app.models.user import User

class _FakeApp:
    """Minimal Flask-like object to satisfy init_db's app.before_request / teardown_appcontext."""

    def before_request(self, f):
        return f

    def teardown_appcontext(self, f):
        return f


init_db(_FakeApp())
db.connect()

db.create_tables([Product, User], safe=True)
print("Tables created.")

# Idempotent: skip seeding if data already exists
if Product.select().count() > 0:
    print(f"Database already has {Product.select().count()} products — skipping product seed.")
else:
    CATEGORIES = ["Electronics", "Clothing", "Books", "Home & Garden", "Sports", "Toys", "Food", "Beauty"]
    ADJECTIVES = ["Premium", "Budget", "Deluxe", "Classic", "Modern", "Vintage", "Smart", "Eco"]
    NOUNS = ["Widget", "Gadget", "Tool", "Device", "Accessory", "Kit", "Set", "Pack"]
 
    products = []
    for i in range(1, 101):
        adj = random.choice(ADJECTIVES)
        noun = random.choice(NOUNS)
        name = f"{adj} {noun} {i}"
        products.append(
            {
                "name": name,
                "category": random.choice(CATEGORIES),
                "description": f"A high-quality {name.lower()} for everyday use.",
                "price": round(random.uniform(1.99, 299.99), 2),
                "stock": random.randint(0, 500),
            }
        )
 
    with db.atomic():
        Product.insert_many(products).execute()
 
    print(f"Seeded {Product.select().count()} products.")
 
# ── Users ─────────────────────────────────────────────────────────────────────
 
if User.select().count() > 0:
    print(f"Database already has {User.select().count()} users — skipping user seed.")
else:
    FIRST_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank",
                   "Ivy", "Jack", "Karen", "Leo", "Mia", "Nate", "Olivia", "Pete"]
    LAST_NAMES  = ["Smith", "Jones", "Lee", "Brown", "Taylor", "Wilson", "Davis",
                   "Clark", "Hall", "Young", "Allen", "King", "Scott", "Green", "Adams"]
 
    users = []
    for i in range(1, 401):
        first = random.choice(FIRST_NAMES)
        last  = random.choice(LAST_NAMES)
        username = f"{first.lower()}_{last.lower()}_{i}"
        email    = f"{username}@example.com"
        users.append({"email": email, "username": username})
 
    with db.atomic():
        User.insert_many(users).execute()
 
    print(f"Seeded {User.select().count()} users.")
 
db.close()