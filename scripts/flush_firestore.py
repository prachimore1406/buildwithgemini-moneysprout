# Copyright 2026 Google LLC
"""Flush script to clear all collections in Firestore native database for MoneySprout."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-01-bfb40d59d7ff"

COLLECTIONS = [
    "savings_goals",
    "chores_and_allowance",
    "delayed_gratification_waiting_room",
    "ledger_transactions",
    "discipline_and_etiquette_streaks",
    "badges_and_achievements",
]

def delete_collection(db, coll_name, batch_size=50):
    coll_ref = db.collection(coll_name)
    docs = list(coll_ref.limit(batch_size).stream())
    deleted = 0
    while docs:
        for doc in docs:
            doc.reference.delete()
            deleted += 1
        docs = list(coll_ref.limit(batch_size).stream())
    print(f"  [-] Deleted {deleted} documents from collection '{coll_name}'.")

def flush_database():
    print(f"Connecting to Firestore for project: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    for coll in COLLECTIONS:
        delete_collection(db, coll)
    print("✅ All Firestore collections flushed successfully!")

if __name__ == "__main__":
    flush_database()
