"""
Pytest configuration and global fixtures for AzamLabs.
Guarantees production database cleanliness after test execution.
"""

import pytest
from azamlabs.core.database import db


@pytest.fixture(scope="session", autouse=True)
def clean_database_after_tests():
    """Ensures production database is kept clean of test topologies after the test suite completes."""
    yield
    try:
        db.purge_test_topologies(["prod-cloud-mesh"])
        # Clean any stray test folders
        for folder in db.list_folders():
            if folder["id"] not in ("root", "cybersecurity", "datacenter", "enterprise", "service_provider"):
                db.delete_folder(folder["id"], delete_topologies=True)
    except Exception as e:
        print(f"Warning during test database cleanup: {e}")
