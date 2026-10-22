import sqlite3
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = r"C:\Users\Yash\Desktop\Exploration\GitHub Master\backend"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.config import DB_PATH

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT category_id, COUNT(*) FROM repositories GROUP BY category_id;")
cat_counts = cursor.fetchall()
print("Category counts:")
for cat, count in cat_counts:
    print(f"  {cat}: {count} repos")

print("\nSample repos from ai-ml:")
cursor.execute("SELECT full_name, stars, topics, description FROM repositories WHERE category_id = 'ai-ml' LIMIT 10;")
for r in cursor.fetchall():
    print(" ", r[0], f"({r[1]} stars)", "Topics:", r[2])

print("\nSample repos from web-frameworks:")
cursor.execute("SELECT full_name, stars, topics, description FROM repositories WHERE category_id = 'web-frameworks' LIMIT 10;")
for r in cursor.fetchall():
    print(" ", r[0], f"({r[1]} stars)", "Topics:", r[2])
