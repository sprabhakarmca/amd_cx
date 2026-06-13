from typing import List, Dict, Optional
import json
from pathlib import Path

class KnowledgeBase:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.kb_file = self.base_dir / "knowledge_base.json"
        self._ensure_default_kb()

    def _ensure_default_kb(self):
        if not self.kb_file.exists():
            self._save_kb(self.get_default_content())

    def _load_kb(self) -> List[Dict]:
        try:
            with open(self.kb_file, 'r') as f:
                return json.load(f)
        except:
            return []

    def _save_kb(self, data: List[Dict]):
        with open(self.kb_file, 'w') as f:
            json.dump(data, f, indent=2)

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        kb = self._load_kb()
        query_lower = query.lower()
        results = []

        keywords_map = {
            'installation': ['Installation Process', 'Installation Wait Time'],
            'warranty': ['Warranty Information'],
            'cancellation': ['Cancellation Policy'],
            'return': ['Return Process'],
            'delivery': ['Delivery Timeline'],
            'tracking': ['Tracking Your Order'],
            'support': ['Contact Support'],
            'assembly': ['Product Assembly'],
            'payment': ['Payment Options'],
        }

        matched_titles = set()
        for keyword, titles in keywords_map.items():
            if keyword in query_lower:
                matched_titles.update(titles)

        if not matched_titles:
            return []

        for item in kb:
            if item['title'] in matched_titles:
                results.append({**item, 'relevance_score': 5})

        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results[:top_k]

    def get_all(self) -> List[Dict]:
        return self._load_kb()

    def add(self, title: str, content: str, tags: List[str]) -> Dict:
        kb = self._load_kb()
        new_item = {
            'id': len(kb) + 1,
            'title': title,
            'content': content,
            'tags': tags
        }
        kb.append(new_item)
        self._save_kb(kb)
        return new_item

    def remove(self, kb_id: int) -> bool:
        kb = self._load_kb()
        kb = [item for item in kb if item.get('id') != kb_id]
        self._save_kb(kb)
        return True

    @staticmethod
    def get_default_content() -> List[Dict]:
        return [
            {
                'id': 1,
                'title': 'Delivery Timeline',
                'content': 'Standard delivery takes 3-5 business days after order confirmation. For custom or bulk orders, delivery may take 5-7 business days. Customers will receive tracking information via email once the order ships.',
                'tags': ['delivery', 'shipping', 'timeline', 'order']
            },
            {
                'id': 2,
                'title': 'Installation Process',
                'content': 'Installation is typically scheduled within 2 business days after delivery. Our certified technicians will arrive during a 4-hour window you select. Please ensure someone aged 18+ is present to grant access. Installation includes setup, calibration, and a brief walkthrough.',
                'tags': ['installation', 'setup', 'technician', 'schedule']
            },
            {
                'id': 3,
                'title': 'Warranty Information',
                'content': 'All products come with a 1-year limited warranty covering manufacturing defects. Extended warranties (2-3 years) are available for purchase within 30 days of delivery. Warranty does not cover damage from misuse or unauthorized modifications.',
                'tags': ['warranty', 'coverage', 'defects', 'extended']
            },
            {
                'id': 4,
                'title': 'Cancellation Policy',
                'content': 'Orders can be cancelled within 24 hours of placement for a full refund. After 24 hours, a 15% restocking fee applies. Custom or personalized orders cannot be cancelled once production begins.',
                'tags': ['cancellation', 'refund', 'restocking']
            },
            {
                'id': 5,
                'title': 'Return Process',
                'content': 'Returns are accepted within 30 days of delivery for unused items in original packaging. To initiate a return, log into your account and select "Return Request" or call support. Refunds are processed within 5-7 business days after inspection.',
                'tags': ['return', 'refund', 'process']
            },
            {
                'id': 6,
                'title': 'Contact Support',
                'content': 'For immediate assistance, call our support line at 1-800-XXX-XXXX (Mon-Fri 9am-6pm EST). Live chat is available on our website. Email support typically responds within 24 hours. For urgent matters, request a callback through our app.',
                'tags': ['support', 'contact', 'help', 'phone']
            },
            {
                'id': 7,
                'title': 'Installation Wait Time',
                'content': 'After delivery, installation is typically scheduled within 1-2 business days. During peak seasons (Nov-Dec), wait times may extend to 3-5 business days. You will receive a scheduling link via SMS and email to choose your preferred time slot.',
                'tags': ['installation', 'waiting', 'schedule', 'delay']
            },
            {
                'id': 8,
                'title': 'Product Assembly',
                'content': 'Some products require self-assembly. Detailed instructions are included in the box. Assembly videos are available on our website under "Product Support". Basic tools (screwdriver, wrench) are required for most assemblies.',
                'tags': ['assembly', 'instructions', 'self-assembly', 'setup']
            },
            {
                'id': 9,
                'title': 'Payment Options',
                'content': 'We accept major credit cards, PayPal, and financing options through Affirm. Split payments are available for orders over $500. Payment plans range from 3 to 12 months with 0% APR for qualified buyers.',
                'tags': ['payment', 'financing', 'credit', 'paypal']
            },
            {
                'id': 10,
                'title': 'Tracking Your Order',
                'content': 'Track your order by logging into your account and visiting "My Orders". You\'ll see real-time status updates including: Order Placed → Processing → Shipped → Out for Delivery → Delivered. Tracking numbers work across all major shipping carriers.',
                'tags': ['tracking', 'order status', 'delivery']
            }
        ]


knowledge_base = KnowledgeBase()