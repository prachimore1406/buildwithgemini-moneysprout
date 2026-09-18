# ruff: noqa
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

import datetime
import io
import json
import math
import os
import urllib.parse
import uuid
from typing import Optional
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types
from PIL import Image, ImageDraw

from .a2ui_utils import a2ui_callback

# CRITICAL: Hardcode project ID and bucket name as strings for Firestore, GCS & RAG clients
PROJECT_ID = "qwiklabs-gcp-01-bfb40d59d7ff"
BUCKET_NAME = "moneysprout-media-qwiklabs-gcp-01-bfb40d59d7ff"
RAG_CORPUS_NAME = "projects/391165179520/locations/us-central1/ragCorpora/7003757127537786880"

_db: Optional[firestore.Client] = None
_storage: Optional[storage.Client] = None


def get_firestore_client() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def get_storage_client() -> storage.Client:
    global _storage
    if _storage is None:
        _storage = storage.Client(project=PROJECT_ID)
    return _storage


async def generate_memories_callback(callback_context: CallbackContext):
    """Sends all user interactions, financial decisions, and habit events to Memory Bank after each turn."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        pass
    return None


# --- 1. AI IMAGE & VIDEO GENERATION TOOLS ---

def generate_financial_concept_video(concept_description: str, tool_context: ToolContext) -> str:
    """Generates a short animated video for a financial concept to teach kids as they save and work towards goals using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Saves the generated video as an ADK artifact and uploads it directly to public Cloud Storage.

    Args:
        concept_description: The financial concept to illustrate in video (e.g., 'Delayed gratification and saving for a scooter', 'Needs vs Wants choices', 'Piggy bank compound saving').
        tool_context: Injected ADK ToolContext used to record artifacts.

    Returns:
        The direct public Cloud Storage HTTPS URL of the generated video.
    """
    import base64
    import google.auth
    import google.auth.transport.requests
    import requests

    credentials, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    token = credentials.token

    url = f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT_ID}/locations/global/interactions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    prompt = (
        f"A short 5-second vibrant, kid-friendly animated video teaching kids the financial concept of {concept_description}. "
        "Bright colors, clear message, positive financial literacy lesson for MoneySprout."
    )

    payload = {
        "model": "gemini-omni-flash-preview",
        "input": [
            {
                "type": "text",
                "text": prompt,
            }
        ],
        "response_format": [
            {
                "type": "video",
                "aspect_ratio": "16:9",
                "duration": "5s",
            }
        ],
        "generation_config": {
            "video_config": {
                "task": "text_to_video",
            }
        },
    }

    res = requests.post(url, headers=headers, json=payload)
    if res.status_code != 200:
        return f"Failed to generate video with gemini-omni-flash-preview. API Status {res.status_code}: {res.text[:300]}"

    data = res.json()
    video_bytes = None
    mime_type = "video/mp4"

    for step in data.get("steps", []):
        if step.get("type") == "model_output" or "content" in step:
            for item in step.get("content", []):
                if item.get("type") == "video" or "data" in item:
                    raw_data = item.get("data")
                    mime_type = item.get("mime_type", "video/mp4")
                    if isinstance(raw_data, str):
                        video_bytes = base64.b64decode(raw_data)
                    elif isinstance(raw_data, bytes):
                        video_bytes = raw_data

    if not video_bytes:
        return "Failed to extract video bytes from gemini-omni-flash-preview response."

    filename = f"concept_video_{uuid.uuid4().hex[:8]}.mp4"

    # (1) Save video bytes with tool_context.save_artifact so it shows up in Playground's Artifacts panel
    artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # (2) Upload video bytes directly to public Cloud Storage bucket
    storage_client = get_storage_client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob_name = f"concept_videos/{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
    return f"🎬 Short financial concept video generated using gemini-omni-flash-preview and saved to Artifacts! Public URL: {public_url}"


def generate_item_illustration(item_description: str, tool_context: ToolContext) -> str:
    """Generates an image for a MoneySprout savings goal item, piggy bank award badge, or reward certificate illustration using gemini-3.1-flash-lite-image in the global region.

    Saves the generated image as an ADK artifact and uploads it to public Cloud Storage.

    Args:
        item_description: Description of the goal item, trophy award, or certificate illustration (e.g., 'Outdoor Scooter', 'Shiny Golden Piggy Bank Trophy').
        tool_context: Injected ADK ToolContext used to record artifacts.

    Returns:
        The direct public Cloud Storage HTTPS URL of the generated image.
    """
    genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")

    prompt = (
        f"A vibrant, high-quality, kid-friendly digital illustration of {item_description} "
        "for the MoneySprout financial literacy app. Bright colors, celebratory, clean vector art style."
    )

    response = genai_client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    image_bytes = None
    mime_type = "image/png"
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

    if not image_bytes:
        return "Failed to generate image bytes from gemini-3.1-flash-lite-image."

    ext = "png" if "png" in mime_type.lower() else "jpeg"
    filename = f"item_illustration_{uuid.uuid4().hex[:8]}.{ext}"

    # (1) Save with tool_context.save_artifact so it shows up in Playground's Artifacts panel
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # (2) Upload image bytes directly to public Cloud Storage bucket
    storage_client = get_storage_client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob_name = f"generated_items/{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
    return f"🎨 Image illustration generated with gemini-3.1-flash-lite-image and saved to Artifacts! Public URL: {public_url}"


# --- 2. RAG RETRIEVAL TOOL ---

def consult_kids_financial_guardrails(query: str) -> str:
    """Queries the MoneySprout grounded document corpus for child safety guardrails, privacy rules, and educational principles.

    Args:
        query: Topic or question to look up (e.g. 'privacy rules', 'sensitive financial data', 'Needs vs Wants guidelines', 'cooling off room', 'financial etiquette').

    Returns:
        The matched passages from the serverless Vertex AI RAG Corpus.
    """
    import vertexai
    from vertexai.preview import rag

    try:
        vertexai.init(project=PROJECT_ID, location="us-central1")
        resp = rag.retrieval_query(
            text=query,
            rag_resources=[rag.RagResource(rag_corpus=RAG_CORPUS_NAME)],
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=3),
        )
        contexts = getattr(resp.contexts, "contexts", [])
        passages = [c.text.strip() for c in contexts if getattr(c, "text", "").strip()]
        return "\n\n---\n\n".join(passages) or "No relevant guardrail passages found in corpus."
    except Exception as e:
        return f"RAG retrieval query failed: {e}"


# --- 3. SAVINGS GOALS TOOLS ---

def get_savings_goals() -> str:
    """Reads all savings goals from the Firestore database.

    Returns:
        A list of active and completed savings goals with target amounts and savings progress.
    """
    db = get_firestore_client()
    docs = db.collection("savings_goals").stream()
    goals = []
    for doc in docs:
        data = doc.to_dict()
        status = "COMPLETED ✅" if data.get("is_achieved") else "IN PROGRESS ⏳"
        goals.append(
            f"• [{status}] Goal ID: {data.get('goal_id')} | Item: '{data.get('item_name')}' ({data.get('category')}) | "
            f"Saved: ${data.get('current_saved', 0.0):.2f} / Target: ${data.get('target_amount', 0.0):.2f} | "
            f"Weekly Rate: ${data.get('weekly_savings', 0.0):.2f}/wk | Notes: {data.get('notes', '')}"
        )

    if not goals:
        return "No savings goals found in Firestore database."
    return "Current Savings Goals in Database:\n" + "\n".join(goals)


def add_or_update_savings_goal(
    goal_id: str,
    item_name: str,
    target_amount: float,
    current_saved: float,
    category: str,
    weekly_savings: float,
    notes: str = "",
) -> str:
    """Creates or updates a savings goal item in the Firestore database.

    Args:
        goal_id: Unique string identifier for the goal (e.g. 'goal_scooter', 'goal_bike').
        item_name: Descriptive name of the goal item.
        target_amount: Target goal price in dollars.
        current_saved: Current amount saved so far in dollars.
        category: Category of item, e.g., 'Need' or 'Want'.
        weekly_savings: Target weekly savings rate in dollars.
        notes: Optional extra notes about the goal or habit streak.

    Returns:
        Confirmation message of database update.
    """
    db = get_firestore_client()
    is_achieved = current_saved >= target_amount
    goal_data = {
        "goal_id": goal_id,
        "item_name": item_name,
        "category": category,
        "target_amount": float(target_amount),
        "current_saved": float(current_saved),
        "weekly_savings": float(weekly_savings),
        "is_achieved": is_achieved,
        "notes": notes,
    }
    db.collection("savings_goals").document(goal_id).set(goal_data)
    status_str = "achieved and completed! 🎉" if is_achieved else "updated in database! ⏳"
    return f"Savings goal '{item_name}' (ID: {goal_id}) successfully {status_str}"


def record_savings_deposit(goal_id: str, deposit_amount: float) -> str:
    """Records a new money deposit towards an existing savings goal in Firestore.

    Args:
        goal_id: The ID of the goal (e.g. 'goal_scooter').
        deposit_amount: The dollar amount being saved/deposited.

    Returns:
        Updated savings total, progress percentage, and financial encouragement.
    """
    db = get_firestore_client()
    doc_ref = db.collection("savings_goals").document(goal_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Savings goal '{goal_id}' not found in database. Create it first using add_or_update_savings_goal!"

    data = doc.to_dict()
    new_saved = data.get("current_saved", 0.0) + float(deposit_amount)
    target = data.get("target_amount", 1.0)
    is_achieved = new_saved >= target

    doc_ref.update({
        "current_saved": new_saved,
        "is_achieved": is_achieved,
    })

    progress = (new_saved / target) * 100 if target > 0 else 100.0
    status_msg = "🎉 GOAL ACHIEVED! Great discipline!" if is_achieved else f"Progress: {progress:.1f}%"
    return (
        f"Deposited ${deposit_amount:.2f} to '{data.get('item_name')}'. "
        f"New Total Saved: ${new_saved:.2f} / ${target:.2f} ({status_msg})."
    )


# --- 4. CHORES & ALLOWANCE TOOLS ---

def get_chores_and_allowance() -> str:
    """Reads active household chores and allowance payouts from Firestore.

    Returns:
        List of chores, payout rewards, and completion status.
    """
    db = get_firestore_client()
    docs = db.collection("chores_and_allowance").stream()
    chores = []
    for doc in docs:
        d = doc.to_dict()
        chores.append(
            f"• [{d.get('status', 'pending').upper()}] Chore ID: {d.get('chore_id')} | Title: '{d.get('title')}' | "
            f"Reward: ${d.get('reward_amount', 0.0):.2f} ({d.get('frequency')}) | Notes: {d.get('notes', '')}"
        )
    if not chores:
        return "No chores found in database."
    return "Household Chores & Allowance List:\n" + "\n".join(chores)


def complete_chore(chore_id: str) -> str:
    """Marks a chore as completed and ready for parent allowance verification.

    Args:
        chore_id: The ID of the chore (e.g. 'chore_clean_room').

    Returns:
        Confirmation message with earned reward details.
    """
    db = get_firestore_client()
    doc_ref = db.collection("chores_and_allowance").document(chore_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Chore '{chore_id}' not found."

    d = doc.to_dict()
    doc_ref.update({"status": "completed"})
    return (
        f"Great job! Marked chore '{d.get('title')}' (ID: {chore_id}) as COMPLETED! "
        f"Earned allowance reward of ${d.get('reward_amount', 0.0):.2f}. Remember to thank your parents!"
    )


# --- 5. DELAYED GRATIFICATION WAITING ROOM TOOLS ---

def get_waiting_room_items() -> str:
    """Reads items in the 7-Day Cooling Off Waiting Room to prevent impulse buying.

    Returns:
        List of wishlist items undergoing the cooling off period.
    """
    db = get_firestore_client()
    docs = db.collection("delayed_gratification_waiting_room").stream()
    items = []
    for doc in docs:
        d = doc.to_dict()
        days_left = d.get('cool_off_days_left', 0)
        status_str = f"Cooling Off ({days_left} days left) ⏳" if days_left > 0 else "Ready for Decision! 💡"
        items.append(
            f"• [{status_str}] Item: '{d.get('item_name')}' | Cost: ${d.get('cost', 0.0):.2f} | "
            f"ID: {d.get('wishlist_id')} | Notes: {d.get('notes', '')}"
        )
    if not items:
        return "The 7-Day Cooling Off Waiting Room is currently empty."
    return "Delayed Gratification Waiting Room Items:\n" + "\n".join(items)


def add_to_waiting_room(item_name: str, cost: float, notes: str = "") -> str:
    """Adds a fun impulse Want item to the 7-Day Cooling Off Waiting Room.

    Args:
        item_name: Name of the desired item.
        cost: Price of the item in dollars.
        notes: Why the child wants it or impulse details.

    Returns:
        Encouraging message explaining the 7-day cooling off period.
    """
    db = get_firestore_client()
    wishlist_id = f"wish_{uuid.uuid4().hex[:6]}"
    doc_data = {
        "wishlist_id": wishlist_id,
        "item_name": item_name,
        "cost": float(cost),
        "cool_off_days_left": 7,
        "status": "cooling_off",
        "notes": notes or "Impulse item added for 7-day cooling off reflection.",
    }
    db.collection("delayed_gratification_waiting_room").document(wishlist_id).set(doc_data)
    return (
        f"Placed '{item_name}' (${cost:.2f}) into the 7-Day Cooling Off Room (ID: {wishlist_id})! "
        "Waiting 7 days before buying helps us distinguish temporary impulses from true long-term joy."
    )


# --- 6. LEDGER & TRANSACTIONS TOOLS ---

def get_ledger_history() -> str:
    """Reads digital piggy bank transaction history.

    Returns:
        List of income and spending transactions.
    """
    db = get_firestore_client()
    docs = db.collection("ledger_transactions").stream()
    txns = []
    for doc in docs:
        d = doc.to_dict()
        t_type = d.get("type", "txn").upper()
        txns.append(
            f"• [{t_type}] ID: {d.get('transaction_id')} | ${d.get('amount', 0.0):.2f} | "
            f"Category: {d.get('category')} | Notes: {d.get('notes')}"
        )
    if not txns:
        return "No transactions found in ledger."
    return "Digital Piggy Bank Ledger History:\n" + "\n".join(txns)


def record_transaction(txn_type: str, amount: float, category: str, notes: str = "") -> str:
    """Records an income, savings deposit, or spending transaction in the piggy bank ledger.

    Args:
        txn_type: Type of transaction ('income', 'savings_deposit', 'spending').
        amount: Amount in dollars.
        category: Category (e.g. 'Chore Allowance', 'Need Spending', 'Want Spending').
        notes: Explanation or description.

    Returns:
        Confirmation message.
    """
    db = get_firestore_client()
    txn_id = f"txn_{uuid.uuid4().hex[:6]}"
    txn_data = {
        "transaction_id": txn_id,
        "type": txn_type,
        "amount": float(amount),
        "category": category,
        "notes": notes,
    }
    db.collection("ledger_transactions").document(txn_id).set(txn_data)
    return f"Recorded {txn_type.upper()} of ${amount:.2f} ({category}) in ledger! (ID: {txn_id})"


# --- 7. ETIQUETTE & HABIT STREAKS TOOLS ---

def get_etiquette_streaks() -> str:
    """Reads active streaks for financial etiquette and healthy financial habits.

    Returns:
        List of habit streaks and record scores.
    """
    db = get_firestore_client()
    docs = db.collection("discipline_and_etiquette_streaks").stream()
    streaks = []
    for doc in docs:
        d = doc.to_dict()
        streaks.append(
            f"• 🔥 Streak: {d.get('current_streak_days')} days | Habit: '{d.get('habit_name')}' | "
            f"Best: {d.get('best_streak_days')} days | Notes: {d.get('notes')}"
        )
    if not streaks:
        return "No habit streaks recorded yet."
    return "Active Financial Manners & Discipline Streaks:\n" + "\n".join(streaks)


def log_etiquette_event(habit_id: str) -> str:
    """Increments a habit streak when a child demonstrates polite financial etiquette or discipline.

    Args:
        habit_id: ID of the habit (e.g. 'etiquette_thank_you_streak' or 'habit_needs_first').

    Returns:
        Praise message and updated streak total.
    """
    db = get_firestore_client()
    doc_ref = db.collection("discipline_and_etiquette_streaks").document(habit_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Habit streak '{habit_id}' not found."

    d = doc.to_dict()
    new_streak = d.get("current_streak_days", 0) + 1
    best_streak = max(new_streak, d.get("best_streak_days", 0))

    doc_ref.update({
        "current_streak_days": new_streak,
        "best_streak_days": best_streak,
    })
    return (
        f"🌟 Outstanding manners! Incremented streak for '{d.get('habit_name')}' to {new_streak} DAYS! "
        f"(Personal record: {best_streak} days)."
    )


# --- 8. BADGES & ACHIEVEMENTS TOOLS ---

def get_user_badges() -> str:
    """Reads earned trophy badges and achievements.

    Returns:
        List of unlocked badges and descriptions.
    """
    db = get_firestore_client()
    docs = db.collection("badges_and_achievements").stream()
    badges = []
    for doc in docs:
        d = doc.to_dict()
        status = f"UNLOCKED {d.get('icon', '🏆')}" if d.get('unlocked') else "LOCKED 🔒"
        badges.append(f"• [{status}] {d.get('title')}: {d.get('description')}")
    if not badges:
        return "No trophy badges found."
    return "MoneySprout Trophy Badges & Achievements:\n" + "\n".join(badges)


# --- 9. REWARD CERTIFICATE TOOLS ---

def generate_goal_reward_certificate(goal_id: str, child_name: str = "Young Saver", tool_context: Optional[ToolContext] = None) -> str:
    """Generates an official digital savings trophy reward certificate image using Google's Gemini Image Model (gemini-3.1-flash-lite-image) in the global region.

    Saves the generated certificate as an ADK artifact and uploads it to public Cloud Storage.

    Args:
        goal_id: The ID of the savings goal (e.g. 'goal_scooter', 'goal_board_game', or 'goal_winter_coat').
        child_name: Name of the child to personalize the trophy award certificate.
        tool_context: Optional injected ADK ToolContext used to record artifacts.

    Returns:
        The direct public Cloud Storage HTTPS URL of the generated reward certificate image.
    """
    db = get_firestore_client()
    doc = db.collection("savings_goals").document(goal_id).get()

    item_name = "Savings Goal"
    target_amount = 0.0
    if doc.exists:
        data = doc.to_dict()
        item_name = data.get("item_name", "Savings Goal")
        target_amount = data.get("target_amount", 0.0)

    prompt = (
        f"An official, magnificent golden savings award certificate for {child_name} for saving ${target_amount:.2f} towards '{item_name}'. "
        "Vibrant 3D golden trophy ribbon, MoneySprout logo badge, bright celebratory colors, clean kid-friendly award certificate."
    )

    genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    response = genai_client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    image_bytes = None
    mime_type = "image/png"
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

    if not image_bytes:
        return "Failed to generate certificate using Gemini image model."

    ext = "png" if "png" in mime_type.lower() else "jpeg"
    filename = f"cert_{uuid.uuid4().hex[:8]}.{ext}"

    if tool_context:
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=artifact_part)

    storage_client = get_storage_client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob_name = f"certificates/{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
    return f"🏆 Official Gemini AI Savings Award Certificate created for {child_name}! View certificate: {public_url}"


def generate_quickchart_savings_certificate(goal_name: str, saved_amount: float, target_amount: float) -> str:
    """Generates a visual award certificate badge via the QuickChart Public API (found in public-apis directory).

    Args:
        goal_name: Name of the savings goal (e.g. 'Outdoor Scooter' or 'Family Strategy Board Game').
        saved_amount: Dollar amount saved so far.
        target_amount: Total target goal price.

    Returns:
        The direct public image URL generated by the QuickChart API.
    """
    api_key = os.environ.get("QUICKCHART_API_KEY", "")

    pct = min(100, int((saved_amount / target_amount) * 100)) if target_amount > 0 else 100
    chart_config = {
        "type": "radialGauge",
        "data": {
            "datasets": [
                {
                    "data": [pct],
                    "backgroundColor": "#10B981"
                }
            ]
        },
        "options": {
            "domain": [0, 100],
            "trackColor": "#1E293B",
            "centerPercentage": 70,
            "title": {
                "display": True,
                "text": f"MoneySprout Award: {goal_name} (${saved_amount:.0f}/${target_amount:.0f})",
                "fontColor": "#F59E0B",
                "fontSize": 18,
            },
        },
    }

    json_str = urllib.parse.quote(json.dumps(chart_config))
    base_url = "https://quickchart.io/chart"
    params = f"?c={json_str}&w=600&h=350&bkg=0F172A"
    if api_key:
        params += f"&key={api_key}"

    chart_url = base_url + params
    return f"✨ Certificate Badge generated via QuickChart Public API: {chart_url}"


# --- FINANCIAL EDUCATION HELPERS ---

def calculate_savings_timeline(target_amount: float, weekly_savings: float) -> str:
    """Calculates how many weeks it takes to reach a goal and provides a delayed gratification tip."""
    if weekly_savings <= 0:
        return "Saving requires putting aside a small amount each week! Try setting weekly savings to at least $1."

    weeks = math.ceil(target_amount / weekly_savings)
    return (
        f"At ${weekly_savings:.2f} per week, it will take {weeks} weeks to save ${target_amount:.2f}! "
        f"Patience is key to achieving big goals—delayed gratification builds real financial strength!"
    )


def evaluate_needs_vs_wants(item_name: str, item_category: str) -> str:
    """Helps kids categorize items into Needs vs. Wants and gives healthy spending advice."""
    item_lower = item_name.lower()
    needs_keywords = ["jacket", "coat", "shoes", "school", "book", "food", "lunch", "medicine", "helmet"]

    is_need = any(kw in item_lower for kw in needs_keywords) or "essential" in item_category.lower()

    if is_need:
        return (
            f"'{item_name}' sounds like an essential NEED! It's important to prioritize needs "
            "before spending money on extra treats or wants."
        )
    else:
        return (
            f"'{item_name}' sounds like a fun WANT! Wants make life exciting, but practicing delayed gratification "
            "and saving up for them over time helps build great financial discipline."
        )


def get_gratitude_and_etiquette_tip(situation: str) -> str:
    """Provides advice on polite money etiquette and gratitude."""
    sit_lower = situation.lower()
    if "allowance" in sit_lower or "gift" in sit_lower:
        return (
            "When receiving money or an allowance, always say 'Thank you!' with a warm smile. "
            "Expressing appreciation shows maturity and respect for the effort behind the gift."
        )
    elif "asking" in sit_lower or "buy" in sit_lower:
        return (
            "When asking about buying something, use polite phrases like 'Could we please discuss if this fits into our budget?' "
            "Being respectful and understanding about family finances is a sign of great money manners!"
        )
    else:
        return (
            "Always speak politely about money, express gratitude for what you have, "
            "and remember that good manners and financial discipline go hand in hand!"
        )


# --- BUILD A2UI SYSTEM PROMPT WITH A2uiSchemaManager (VERSION 0.8) & BASIC CATALOG ---

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description="MoneySprout, an interactive financial literacy & discipline coach for kids.",
    workflow_description=(
        "Analyze the request, call tools as needed, and return structured A2UI visual cards or plain text when appropriate."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

base_instruction = (
    "You are Sprout 🌱, an interactive, warm, and friendly financial literacy mascot buddy for kids.\n\n"
    "FINANCIAL LITERACY CONCEPT & VIDEO DIALOGUE FLOW:\n"
    "1. FIRST TURN (Concept Introduction):\n"
    "   - When a child asks about their savings progress (e.g., 'How close am I to getting my bike?'), call `get_savings_goals()`.\n"
    "   - Report progress ($85 out of $120 saved) AND introduce the concept of **delayed gratification** right in this 1st response!\n"
    "   - Example: 'You have saved $85 out of $120 for your Outdoor Bicycle (71% of the way there)! This is a super example of **delayed gratification** — saving step-by-step for a big reward instead of spending money right away on quick impulses!'\n\n"
    "2. SECOND TURN (Video & Award Certificate Response):\n"
    "   - When the child asks about the concept (e.g., 'What is delayed gratification?'):\n"
    "   - SAY EXPLICITLY: 'Let\\'s watch this video together so that you understand better with some theory!'\n"
    "   - Call `generate_financial_concept_video('delayed gratification and saving for a bicycle')` to generate the animated concept video using Google's Omni model (`gemini-omni-flash-preview`).\n"
    "   - Call `generate_goal_reward_certificate('goal_bike', 'Young Saver')` to generate the official Gemini AI savings award certificate image using `gemini-3.1-flash-lite-image`.\n"
    "   - CRITICAL: In your text response, ALWAYS include both the HTTPS Video URL (ending in .mp4) and HTTPS Certificate Image URL (ending in .png) verbatim so the frontend embeds the video player and certificate image!\n"
    "   - DO NOT call `get_savings_goals()` in Turn 2, and NEVER output raw database lists, Goal IDs, or technical JSON text.\n\n"
    "GEMINI AI IMAGE & VIDEO GENERATION TOOLS (NO PIL):\n"
    "1. `generate_financial_concept_video()`: Uses Google's Omni model (`gemini-omni-flash-preview`) for animated concept videos.\n"
    "2. `generate_goal_reward_certificate()` & `generate_item_illustration()`: Uses Gemini AI image model (`gemini-3.1-flash-lite-image`) for award certificates, trophy badges, and goal images. NO PIL allowed."
)

full_instruction = f"{base_instruction}\n\n---\n\n{a2ui_instruction}"

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=full_instruction,
    tools=[
        generate_financial_concept_video,
        generate_item_illustration,
        consult_kids_financial_guardrails,
        get_savings_goals,
        add_or_update_savings_goal,
        record_savings_deposit,
        get_chores_and_allowance,
        complete_chore,
        get_waiting_room_items,
        add_to_waiting_room,
        get_ledger_history,
        record_transaction,
        get_etiquette_streaks,
        log_etiquette_event,
        get_user_badges,
        generate_goal_reward_certificate,
        generate_quickchart_savings_certificate,
        calculate_savings_timeline,
        evaluate_needs_vs_wants,
        get_gratitude_and_etiquette_tip,
        PreloadMemoryTool(),
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
