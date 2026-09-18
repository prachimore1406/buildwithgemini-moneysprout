# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Seed script to populate initial MoneySprout data into Firestore native database."""

from google.cloud import firestore

# CRITICAL: Hardcode project ID as string (do not use GOOGLE_CLOUD_PROJECT or google.auth.default)
PROJECT_ID = "qwiklabs-gcp-01-bfb40d59d7ff"

SEED_SAVINGS_GOALS = [
    {
        "goal_id": "goal_cycle",
        "item_name": "New Bicycle",
        "category": "Want",
        "target_amount": 60.00,
        "current_saved": 15.00,
        "weekly_savings": 5.00,
        "is_achieved": False,
        "notes": "Saving weekly allowance for a new bicycle to ride with friends.",
    },
    {
        "goal_id": "goal_scooter",
        "item_name": "Outdoor Scooter",
        "category": "Want",
        "target_amount": 50.00,
        "current_saved": 25.00,
        "weekly_savings": 5.00,
        "is_achieved": False,
        "notes": "Practicing delayed gratification and saving weekly allowance.",
    },
    {
        "goal_id": "goal_board_game",
        "item_name": "Family Strategy Board Game",
        "category": "Want",
        "target_amount": 30.00,
        "current_saved": 15.00,
        "weekly_savings": 3.00,
        "is_achieved": False,
        "notes": "Buying a game for family game night.",
    },
    {
        "goal_id": "goal_winter_coat",
        "item_name": "Warm Winter Coat",
        "category": "Need",
        "target_amount": 45.00,
        "current_saved": 45.00,
        "weekly_savings": 10.00,
        "is_achieved": True,
        "notes": "Essential need priority item — goal fully completed!",
    },
]

SEED_CHORES = [
    {
        "chore_id": "chore_clean_room",
        "title": "Clean Study Desk & Organize Books",
        "reward_amount": 2.50,
        "frequency": "weekly",
        "status": "pending",
        "notes": "Keep study space tidy to earn weekly allowance.",
    },
    {
        "chore_id": "chore_water_plants",
        "title": "Water Backyard Garden Plants",
        "reward_amount": 1.50,
        "frequency": "daily",
        "status": "completed",
        "notes": "Watered flowers respectfully in the morning.",
    },
    {
        "chore_id": "chore_feed_pets",
        "title": "Feed & Walk Dog Benny",
        "reward_amount": 2.00,
        "frequency": "daily",
        "status": "pending",
        "notes": "Take care of household pet responsibilities.",
    },
]

SEED_WAITING_ROOM = [
    {
        "wishlist_id": "wish_mystery_box",
        "item_name": "Collector Mystery Toy Box",
        "cost": 12.00,
        "cool_off_days_left": 5,
        "status": "cooling_off",
        "notes": "Impulse item placed in 7-day cooling off room to test real desire.",
    },
    {
        "wishlist_id": "wish_comic_book",
        "item_name": "Superhero Comic Book Vol 2",
        "cost": 8.00,
        "cool_off_days_left": 0,
        "status": "ready_to_decide",
        "notes": "7 days completed! Ready to decide if worth buying or saving.",
    },
]

SEED_LEDGER = [
    {
        "transaction_id": "txn_001",
        "type": "income",
        "amount": 10.00,
        "category": "Chore Allowance",
        "notes": "Earned from completing weekly chores with great care.",
    },
    {
        "transaction_id": "txn_002",
        "type": "savings_deposit",
        "amount": 5.00,
        "category": "Goal Deposit",
        "notes": "Deposited into Outdoor Scooter savings goal.",
    },
]

SEED_STREAKS = [
    {
        "habit_id": "etiquette_thank_you_streak",
        "habit_name": "Said Thank You for Allowance & Gifts",
        "current_streak_days": 14,
        "best_streak_days": 14,
        "notes": "Polite manners streak active!",
    },
    {
        "habit_id": "habit_needs_first",
        "habit_name": "Evaluated Need vs Want Before Asking",
        "current_streak_days": 7,
        "best_streak_days": 10,
        "notes": "Good financial discipline habit.",
    },
]

SEED_BADGES = [
    {
        "badge_id": "badge_gratitude_guru",
        "title": "Gratitude Guru",
        "description": "Expressed sincere thankfulness 10 times when receiving allowance or gifts",
        "icon": "🙏",
        "unlocked": True,
    },
    {
        "badge_id": "badge_master_saver",
        "title": "Master Saver",
        "description": "Saved over $50 towards personal goals with patience",
        "icon": "🏆",
        "unlocked": True,
    },
    {
        "badge_id": "badge_needs_first",
        "title": "Needs First",
        "description": "Prioritized essential needs before purchasing extra wants",
        "icon": "🌟",
        "unlocked": False,
    },
]


def seed_database():
    print(f"Connecting to Firestore for project: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)

    # 1. Savings Goals
    for goal in SEED_SAVINGS_GOALS:
        doc_ref = db.collection("savings_goals").document(goal["goal_id"])
        doc_ref.set(goal)
        print(f"  [+] Seeded savings goal: '{goal['item_name']}' (ID: {goal['goal_id']})")

    # 2. Chores & Allowance
    for chore in SEED_CHORES:
        doc_ref = db.collection("chores_and_allowance").document(chore["chore_id"])
        doc_ref.set(chore)
        print(f"  [+] Seeded chore: '{chore['title']}' (ID: {chore['chore_id']})")

    # 3. Waiting Room
    for wish in SEED_WAITING_ROOM:
        doc_ref = db.collection("delayed_gratification_waiting_room").document(wish["wishlist_id"])
        doc_ref.set(wish)
        print(f"  [+] Seeded waiting room item: '{wish['item_name']}' (ID: {wish['wishlist_id']})")

    # 4. Ledger
    for txn in SEED_LEDGER:
        doc_ref = db.collection("ledger_transactions").document(txn["transaction_id"])
        doc_ref.set(txn)
        print(f"  [+] Seeded transaction: '{txn['transaction_id']}' (${txn['amount']:.2f})")

    # 5. Etiquette Streaks
    for streak in SEED_STREAKS:
        doc_ref = db.collection("discipline_and_etiquette_streaks").document(streak["habit_id"])
        doc_ref.set(streak)
        print(f"  [+] Seeded etiquette streak: '{streak['habit_name']}' (ID: {streak['habit_id']})")

    # 6. Badges
    for badge in SEED_BADGES:
        doc_ref = db.collection("badges_and_achievements").document(badge["badge_id"])
        doc_ref.set(badge)
        print(f"  [+] Seeded badge: '{badge['title']}' {badge['icon']}")

    print("✅ All 6 Firestore collections seeded successfully!")


if __name__ == "__main__":
    seed_database()
