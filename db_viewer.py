
from database import db_manager

pages = db_manager.get_pages_by_parent('')
if pages:
    print(f"Found {len(pages)} pages:")
    for p in pages:
        print(f"  - ID: {p.page_id}, Title: {p.title}")
else:
    print("No pages found in the database.")
