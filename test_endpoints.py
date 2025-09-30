# test_endpoints.py
from app_flask import app

# Print all registered routes
print("📋 Registered endpoints:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.rule} - {list(rule.methods)}")
    