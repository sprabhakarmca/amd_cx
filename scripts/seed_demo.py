import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vector_store import vector_store
from app.services.review_service import review_service
from app.services.database import db
from app.services.metrics import metrics_service
from datetime import datetime, timedelta
import uuid

def clear_existing_data():
    print("Clearing existing data...")
    try:
        db.execute("DELETE FROM feedbacks")
        print("  Deleted feedbacks")
    except Exception as e:
        print(f"  Error clearing feedbacks: {e}")
    try:
        db.execute("DELETE FROM reviews")
        print("  Deleted reviews")
    except Exception as e:
        print(f"  Error clearing reviews: {e}")

def seed_demo_data():
    clear_existing_data()
    print("Seeding demo data with hierarchical taxonomy...")

    demo_entries = [
        {
            "feedback_text": "Love the new dark mode feature! It's so much easier on my eyes at night.",
            "product": "WebStore", "nps_score": 10, "user_id": "user-bob-002",
            "categories": ["features.missing_feature"],
            "needs_review": False, "assigned_team": "none",
            "status": "resolved", "human_response": None,
            "created_at": (datetime.now() - timedelta(days=1)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "Delivery was super fast! Got my order in 2 days.",
            "product": "MobileApp", "nps_score": 10, "user_id": "user-emma-005",
            "categories": ["delivery.late_delivery"],
            "needs_review": False, "assigned_team": "none",
            "status": "resolved", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=12)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "The checkout process is confusing. I spent 10 minutes trying to find the payment button.",
            "product": "WebStore", "nps_score": 4, "user_id": "user-alice-001",
            "categories": ["usability.checkout_difficulty"],
            "needs_review": True, "assigned_team": "Product Team",
            "status": "resolved",
            "human_response": "Hi Alice, we fixed the checkout flow. The payment button is now more visible.",
            "created_at": (datetime.now() - timedelta(days=2)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "Your live chat keeps saying 'Connecting...' forever. I just want to know why I was charged twice.",
            "product": "MobileApp", "nps_score": 2, "user_id": "user-charlie-003",
            "categories": ["support.chatbot_frustration", "billing.double_charge"],
            "needs_review": True, "assigned_team": "Billing Team",
            "status": "resolved",
            "human_response": "Hi Charlie, we resolved the duplicate charge. Refund processed.",
            "created_at": (datetime.now() - timedelta(hours=18)).isoformat(), "kb_references": ["Contact Support"]
        },
        {
            "feedback_text": "The product recommendations are not relevant to my interests anymore.",
            "product": "WebStore", "nps_score": 5, "user_id": "user-diana-004",
            "categories": ["features.feature_not_working"],
            "needs_review": False, "assigned_team": "none",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=6)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "Would be great to have a wishlist feature for saved items.",
            "product": "WebStore", "nps_score": 7, "user_id": "user-henry-008",
            "categories": ["features.missing_feature"],
            "needs_review": False, "assigned_team": "none",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=1)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "The delivery was late, and the installation technician was unprepared. When I asked about warranty, they couldn't answer.",
            "product": "WebStore", "nps_score": 2, "user_id": "prabhu",
            "categories": ["delivery.late_delivery", "installation.technician_unprofessional"],
            "needs_review": True, "assigned_team": "Delivery Team",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "kb_references": ["Delivery Timeline", "Installation Process"]
        },
        {
            "feedback_text": "My order arrived 5 days late. The tracking showed it was still in transit even after delivery.",
            "product": "MobileApp", "nps_score": 3, "user_id": "user-raj-009",
            "categories": ["delivery.late_delivery", "delivery.delivery_communication"],
            "needs_review": True, "assigned_team": "Delivery Team",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=4)).isoformat(), "kb_references": ["Delivery Timeline"]
        },
        {
            "feedback_text": "I purchased an extended warranty but when I tried to file a claim, I was told my product wasn't eligible.",
            "product": "WebStore", "nps_score": 4, "user_id": "user-sara-010",
            "categories": ["warranty.claim_denied", "trust.misleading_advertising"],
            "needs_review": True, "assigned_team": "Warranty Team",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=8)).isoformat(), "kb_references": ["Warranty Information"]
        },
        {
            "feedback_text": "I tried to cancel my order within 24 hours but the system didn't let me.",
            "product": "MobileApp", "nps_score": 3, "user_id": "user-amy-011",
            "categories": ["cancellation.cancellation_difficult"],
            "needs_review": True, "assigned_team": "Billing Team",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=12)).isoformat(), "kb_references": ["Cancellation Policy"]
        },
        {
            "feedback_text": "The product arrived damaged and I need to return it.",
            "product": "WebStore", "nps_score": 4, "user_id": "user-bob-002",
            "categories": ["delivery.damaged_in_transit", "cancellation.return_label_issue"],
            "needs_review": True, "assigned_team": "Delivery Team",
            "status": "resolved",
            "human_response": "Hi Bob, pickup arranged. No need to print anything.",
            "created_at": (datetime.now() - timedelta(days=1)).isoformat(), "kb_references": ["Return Process"]
        },
        {
            "feedback_text": "The assembly instructions were unclear and some parts were missing.",
            "product": "WebStore", "nps_score": 5, "user_id": "user-raj-009",
            "categories": ["assembly.instructions_unclear", "assembly.missing_parts"],
            "needs_review": True, "assigned_team": "Product Team",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=3)).isoformat(), "kb_references": ["Product Assembly"]
        },
        {
            "feedback_text": "Been overcharged for shipping on a small item. The cost was more than the product itself!",
            "product": "WebStore", "nps_score": 3, "user_id": "user-frank-006",
            "categories": ["pricing.shipping_cost_unreasonable", "billing.incorrect_charge"],
            "needs_review": True, "assigned_team": "Billing Team",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=5)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "I keep getting logged out of my account every few minutes. It's impossible to complete a purchase.",
            "product": "MobileApp", "nps_score": 2, "user_id": "user-grace-007",
            "categories": ["account.session_expiry_frequent", "usability.checkout_difficulty"],
            "needs_review": True, "assigned_team": "Product Team",
            "status": "resolved",
            "human_response": "Hi Grace, we fixed the session timeout issue. You should stay logged in now.",
            "created_at": (datetime.now() - timedelta(days=3)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "The email confirmation never arrived, but the order still went through. I had no tracking info for 3 days.",
            "product": "WebStore", "nps_score": 4, "user_id": "user-ivan-012",
            "categories": ["communication.missing_order_confirmation", "delivery.delivery_communication"],
            "needs_review": False, "assigned_team": "none",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=10)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "Product page showed 'in stock' but after ordering I was told it's on backorder for 6 weeks. This feels deceptive.",
            "product": "WebStore", "nps_score": 1, "user_id": "user-jack-013",
            "categories": ["trust.misleading_advertising", "communication.misleading_promotion"],
            "needs_review": True, "assigned_team": "Product Team",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=7)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "The subscription auto-renewed without any warning email. I was charged for a full year I didn't want.",
            "product": "MobileApp", "nps_score": 2, "user_id": "user-kate-014",
            "categories": ["billing.subscription_billing", "communication.notification_delay"],
            "needs_review": True, "assigned_team": "Billing Team",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=9)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "Two-factor authentication keeps sending codes to my old phone number that I already updated in settings.",
            "product": "WebStore", "nps_score": 3, "user_id": "user-leo-015",
            "categories": ["account.multi_factor_issue", "account.profile_update_fails"],
            "needs_review": True, "assigned_team": "Product Team",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=11)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "The delivery driver was incredibly friendly and helpful. He carried the heavy box all the way to my kitchen.",
            "product": "WebStore", "nps_score": 10, "user_id": "user-mia-016",
            "categories": ["delivery.courier_behavior"],
            "needs_review": False, "assigned_team": "none",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=1)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "I've submitted three support tickets and nobody has responded. It's been over a week for a simple question.",
            "product": "MobileApp", "nps_score": 1, "user_id": "user-noah-017",
            "categories": ["support.ticket_stuck", "customer_service.no_follow_up"],
            "needs_review": True, "assigned_team": "General Support",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=14)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "The site layout changed and now I can't find the order history. Why fix what wasn't broken?",
            "product": "WebStore", "nps_score": 5, "user_id": "user-olivia-018",
            "categories": ["usability.confusing_navigation", "features.limited_customization"],
            "needs_review": False, "assigned_team": "none",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=13)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "Your return policy says free returns but I had to pay for shipping myself. The fine print is ridiculous.",
            "product": "WebStore", "nps_score": 3, "user_id": "user-liam-019",
            "categories": ["trust.hidden_terms", "cancellation.return_label_issue"],
            "needs_review": True, "assigned_team": "Billing Team",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=16)).isoformat(), "kb_references": ["Return Process"]
        },
        {
            "feedback_text": "The appliance works great but the installation technician left a mess and didn't clean up.",
            "product": "WebStore", "nps_score": 6, "user_id": "user-sophia-020",
            "categories": ["installation.cleanup_not_done", "installation.technician_unprofessional"],
            "needs_review": True, "assigned_team": "Delivery Team",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=20)).isoformat(), "kb_references": ["Installation Process"]
        },
        {
            "feedback_text": "I love the quality of the furniture! The wood finish is beautiful and the cushions are very comfortable.",
            "product": "WebStore", "nps_score": 9, "user_id": "user-ava-021",
            "categories": ["product.material_quality", "product.durability"],
            "needs_review": False, "assigned_team": "none",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(days=1, hours=-2)).isoformat(), "kb_references": []
        },
        {
            "feedback_text": "Contacted customer service about a missing part and they transferred me 4 times. Nobody could help.",
            "product": "MobileApp", "nps_score": 2, "user_id": "user-ethan-022",
            "categories": ["customer_service.excessive_transfers", "customer_service.unresolved_issue"],
            "needs_review": True, "assigned_team": "General Support",
            "status": "pending", "human_response": None,
            "created_at": (datetime.now() - timedelta(hours=15)).isoformat(), "kb_references": []
        }
    ]

    for entry in demo_entries:
        feedback_id = vector_store.add_feedback(
            feedback_text=entry["feedback_text"],
            product=entry["product"],
            nps_score=entry["nps_score"],
            user_id=entry["user_id"],
            categories=entry["categories"],
            needs_review=entry.get("needs_review", False),
            assigned_team=entry.get("assigned_team", "none"),
            kb_references=entry.get("kb_references", []),
            created_at=entry["created_at"]
        )

        vector_store.store_embedding(
            feedback_id=feedback_id,
            feedback_text=entry["feedback_text"],
            product=entry["product"],
            categories=entry["categories"],
            nps_score=entry["nps_score"],
            user_id=entry["user_id"],
            created_at=entry["created_at"]
        )

        if entry.get("needs_review") and entry.get("assigned_team") != "none":
            review_service.create_review(
                feedback_id=feedback_id,
                feedback_text=entry["feedback_text"],
                product=entry["product"],
                nps_score=entry["nps_score"],
                categories=entry["categories"],
                assigned_team=entry["assigned_team"],
                original_response="",
                user_id=entry["user_id"],
                is_technical=False,
                duplicate_note=None,
                intent_note=None
            )

            if entry.get("status") == "resolved":
                db.execute(
                    "UPDATE reviews SET status=%s, final_response=%s WHERE feedback_id=%s",
                    ["resolved", entry["human_response"] or "", feedback_id]
                )

    for entry in demo_entries:
        parent = entry["categories"][0].split(".")[0] if entry["categories"] else "general"
        metrics_service.record_classification(
            feedback_text=entry["feedback_text"],
            categories=[{"category": parent, "subcategory": entry["categories"][0].split(".")[1] if len(entry["categories"][0].split(".")) > 1 else "", "confidence": 0.95, "is_primary": True}],
            latency_ms=0,
            confidence=0.95,
            needs_review=entry.get("needs_review", False),
            assigned_team=entry.get("assigned_team", "General Support")
        )

    print(f"Seeded {len(demo_entries)} demo entries.")
    print(f"  - Positive (no review): {sum(1 for e in demo_entries if not e.get('needs_review'))}")
    print(f"  - Needs review: {sum(1 for e in demo_entries if e.get('needs_review'))}")

if __name__ == "__main__":
    seed_demo_data()
