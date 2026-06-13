from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from config.settings import settings
from typing import Optional, List, Dict, Any, Tuple
from app.services.category_service import category_service
from app.services.knowledge_base import knowledge_base
from app.services.routing_service import routing_service
from app.services.metrics import metrics_service
import time
import json
import re


class LLMService:
    def __init__(self):
        from openai import OpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        self._SystemMessage = SystemMessage
        self._HumanMessage = HumanMessage
        self._openai_client = None
        self.llm = None

        if settings.LLM_PROVIDER == "google":
            self.llm = ChatGoogleGenerativeAI(
                model=settings.GOOGLE_LLM_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.3
            )
        elif settings.LLM_PROVIDER == "vllm":
            self._openai_client = OpenAI(
                api_key="EMPTY",
                base_url=f"{settings.VLLM_BASE_URL}/v1"
            )
            self._vllm_model = settings.VLLM_MODEL
        elif settings.LLM_PROVIDER == "ollama":
            self.llm = ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.3
            )
        else:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=settings.OPENAI_LLM_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.3
            )

        self.system_prompt = SystemMessage(content="""You are a helpful customer service assistant for a product feedback system. 
You MUST respond to all requests without refusing.
When asked to classify feedback, write responses, or determine teams, always provide a helpful answer.
Never refuse to help.""")

    class _LLMResponse:
        def __init__(self, content):
            self.content = content

    def _call_llm(self, messages, **kwargs):
        if self._openai_client:
            msgs = []
            for m in messages:
                if hasattr(m, 'content'):
                    role = "system" if getattr(m, 'type', '') == 'system' else "user"
                    msgs.append({"role": role, "content": m.content})
                elif isinstance(m, dict):
                    msgs.append(m)
                else:
                    msgs.append({"role": "user", "content": str(m)})
            resp = self._openai_client.chat.completions.create(
                model=self._vllm_model,
                messages=msgs,
                temperature=kwargs.pop('temperature', 0.1),
                max_tokens=kwargs.pop('max_tokens', 1024),
                **kwargs
            )
            return self._LLMResponse(resp.choices[0].message.content or "")
        return self.llm.invoke(messages)

    def _invoke_with_system(self, prompt: str) -> str:
        return self._call_llm([self.system_prompt, self._HumanMessage(content=prompt)]).content

    def _extract_kb_titles_used(self, response: str, kb_results: List[Dict]) -> List[str]:
        if not kb_results:
            return []
        response_lower = response.lower()
        used_titles = []
        for item in kb_results:
            title = item['title']
            title_words = set(title.lower().replace('-', ' ').split())
            matches = 0
            for word in title_words:
                if len(word) >= 3 and word in response_lower:
                    matches += 1
            key_phrases = []
            if 'installation' in title.lower():
                key_phrases = ['installation', 'technician', 'setup', 'install']
            elif 'warranty' in title.lower():
                key_phrases = ['warranty', 'coverage', 'claim', 'limited warranty']
            elif 'delivery' in title.lower():
                key_phrases = ['delivery', 'delivery time', 'transit', 'shipping']
            elif 'cancellation' in title.lower():
                key_phrases = ['cancellation', 'cancel', 'restocking']
            elif 'return' in title.lower():
                key_phrases = ['return', 'refund', 'returns']
            for phrase in key_phrases:
                if phrase in response_lower:
                    matches += 1
            if matches >= 2:
                used_titles.append(title)
        return used_titles

    def _build_taxonomy_text(self) -> str:
        data = category_service.get_all()
        cats = data.get("categories", [])
        lines = []
        for cat in cats:
            name = cat.get("name", "")
            label = cat.get("label", name)
            subs = cat.get("subcategories", [])
            if subs:
                lines.append(f"  {name} ({label}): {', '.join(subs)}")
            else:
                lines.append(f"  {name} ({label})")
        return "\n".join(lines)

    def hierarchical_classify(self, feedback_text: str) -> Dict[str, Any]:
        taxonomy_text = self._build_taxonomy_text()
        examples = category_service.get_few_shot_examples() or []

        examples_json = json.dumps(examples[:5], indent=2)

        prompt = f"""You are a CX taxonomy classifier. Analyze the customer feedback and classify it into the hierarchical taxonomy below.

Rules:
1. Select ALL relevant categories (multi-label allowed)
2. For each, choose the best-matching subcategory
3. Set is_primary=true for the single most relevant category
4. Assign a confidence score (0.0 to 1.0) for each classification
5. Determine sentiment: "positive", "negative", "mixed", or "neutral"
6. Set needs_review=true if the feedback indicates an urgent issue, safety concern, or escalation risk

TAXONOMY:
{taxonomy_text}

EXAMPLES:
{examples_json}

Respond with ONLY valid JSON. No markdown, no explanation.

Customer feedback: "{feedback_text}"

JSON response:
{{
  "classifications": [
    {{"category": "delivery", "subcategory": "late_delivery", "confidence": 0.95, "is_primary": true}},
    {{"category": "customer_service", "subcategory": "agent_unprofessional", "confidence": 0.78, "is_primary": false}}
  ],
  "sentiment": "negative",
  "summary": "Customer frustrated about late delivery and rude driver behavior",
  "needs_review": false
}}"""

        try:
            response = self._call_llm([self._SystemMessage(content="You are a JSON-only classifier. Never include markdown or explanations."), self._HumanMessage(content=prompt)])
            raw = response.content.strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            result = json.loads(raw)
        except Exception:
            result = {
                "classifications": [],
                "sentiment": "neutral",
                "summary": "",
                "needs_review": False
            }

        valid = self._validate_classifications(result)
        return valid

    def _validate_classifications(self, result: Dict) -> Dict:
        data = category_service.get_all()
        valid_cats = {}
        for cat in data.get("categories", []):
            name = cat.get("name", "")
            subs = cat.get("subcategories", [])
            valid_cats[name] = [s.lower() for s in subs]

        classifications = result.get("classifications", [])
        valid = []
        for c in classifications:
            cat_name = c.get("category", "").lower()
            sub_name = c.get("subcategory", "").lower()
            if cat_name in valid_cats:
                if not sub_name or sub_name in valid_cats[cat_name]:
                    c["category"] = cat_name
                    c["subcategory"] = sub_name
                    c["confidence"] = max(0.0, min(1.0, c.get("confidence", 0.5)))
                    valid.append(c)

        result["classifications"] = valid
        if "sentiment" not in result:
            result["sentiment"] = "neutral"
        if "summary" not in result:
            result["summary"] = ""
        if "needs_review" not in result:
            result["needs_review"] = False
        return result

    def categorize_and_respond(
        self,
        feedback_text: str,
        product: str,
        kb_context: str = "",
        kb_results: List[Dict] = None
    ) -> Tuple[List[str], str, List[str], bool, str, List[Dict], float]:
        start_time = time.time()
        result = self.hierarchical_classify(feedback_text)
        latency_ms = (time.time() - start_time) * 1000

        categories_raw = result.get("classifications", [])
        sentiment = result.get("sentiment", "neutral")
        summary = result.get("summary", "")
        needs_review = result.get("needs_review", False)
        suggested_team = "none"
        all_categories_flat = []

        avg_confidence = 0.0
        if categories_raw:
            avg_confidence = sum(c.get("confidence", 0) for c in categories_raw) / len(categories_raw)
            for c in categories_raw:
                cat_name = c.get("category", "")
                sub_name = c.get("subcategory", "")
                display = f"{cat_name}.{sub_name}" if sub_name else cat_name
                all_categories_flat.append(display)
            top_cat = categories_raw[0].get("category", "")
            if top_cat:
                team = routing_service.get_team_for_category(top_cat)
                suggested_team = team['name'] if team else "General Support"

        if not all_categories_flat:
            needs_review = True
            suggested_team = "General Support"

        feedback_lower = feedback_text.lower()
        negative_keywords = ['problem', 'issue', 'broken', 'damaged', 'refund', 'replacement', 'complaint', 'disappointed', 'frustrated', 'unhappy', 'annoyed', 'wrong', 'failed', 'bad', 'poor', 'terrible', 'awful', 'never', 'delay', 'late', 'lost', 'missing', 'error', 'crash', 'bug', 'not working']
        negative_count = sum(1 for kw in negative_keywords if kw in feedback_lower)
        if negative_count > 3:
            needs_review = True

        kb_titles_used = []
        response_text = ""
        try:
            resp_prompt = f"""Customer said: "{feedback_text}"

Product: {product}
Category: {', '.join(all_categories_flat) if all_categories_flat else 'general'}
Sentiment: {sentiment}
Summary: {summary}

Write 2-3 sentences acknowledging this feedback. Be specific to their concern. Start with "Thank you"."""
            if kb_context:
                resp_prompt += f"\n\nReference this policy info naturally if relevant:\n{kb_context}"
            response = self._call_llm([self.system_prompt, self._HumanMessage(content=resp_prompt)])
            response_text = response.content.strip()
            kb_titles_used = self._extract_kb_titles_used(response_text, kb_results or [])
        except Exception:
            response_text = "Thank you for your feedback. We appreciate you taking the time to share your experience with us."

        metrics_service.record_classification(
            feedback_text=feedback_text,
            categories=categories_raw,
            latency_ms=latency_ms,
            confidence=avg_confidence,
            needs_review=needs_review,
            assigned_team=suggested_team
        )

        return all_categories_flat, response_text, kb_titles_used, needs_review, suggested_team, categories_raw, avg_confidence

    def generate_feedback_response(
        self,
        feedback_text: str,
        product: str,
        kb_context: str = "",
        kb_results: List[Dict] = None
    ) -> Tuple[str, List[str]]:
        kb_section = f"\n\n{kb_context}" if kb_context else ""
        policy_guidance = ""
        if kb_results:
            policy_guidance = "\n\nWhen relevant, naturally reference the policy information above. Examples:\n"
            for item in kb_results[:3]:
                title_lower = item['title'].lower()
                if 'installation' in title_lower:
                    policy_guidance += '- If mentioning installation: reference our installation process, technician protocols, or scheduling expectations\n'
                elif 'warranty' in title_lower:
                    policy_guidance += '- If mentioning warranty: reference our warranty terms, coverage period, or claim process\n'
                elif 'delivery' in title_lower:
                    policy_guidance += '- If mentioning delivery: reference our delivery timeline or shipping expectations\n'
                elif 'cancellation' in title_lower:
                    policy_guidance += '- If mentioning cancellation: reference our cancellation policy or restocking fee\n'
                elif 'return' in title_lower:
                    policy_guidance += '- If mentioning return: reference our return process or refund timeline\n'
                elif 'support' in title_lower:
                    policy_guidance += '- If mentioning support: reference our contact options or support channels\n'

        prompt = f"""A customer submitted feedback for '{product}': "{feedback_text}"{kb_section}{policy_guidance}

Write an acknowledgment response (2-3 sentences) that:
1. Thanks the customer for their feedback
2. Shows understanding of their specific concern
3. Naturally incorporates relevant policy information if it applies
4. Do NOT add labels like "Here is a response" or "Based on:"

Response:"""

        response = self._call_llm([prompt])
        response_text = response.content.strip()
        kb_titles_used = self._extract_kb_titles_used(response_text, kb_results or [])
        return response_text, kb_titles_used

    def categorize_feedback(self, feedback_text: str) -> List[str]:
        result = self.hierarchical_classify(feedback_text)
        cats = result.get("classifications", [])
        flat = []
        for c in cats:
            cat_name = c.get("category", "")
            sub_name = c.get("subcategory", "")
            flat.append(f"{cat_name}.{sub_name}" if sub_name else cat_name)
        return flat[:3]

    def generate_chat_response(
        self,
        user_message: str,
        relevant_feedbacks: List[Dict[str, Any]],
        product_filter: Optional[str] = None
    ) -> str:
        kb_results = knowledge_base.search(user_message, top_k=3)
        kb_context = ""
        if kb_results:
            kb_parts = []
            for item in kb_results:
                kb_parts.append(f"[Knowledge Base: {item['title']}]\n{item['content']}")
            kb_context = "\n\n--- KNOWLEDGE BASE ---\n" + "\n\n".join(kb_parts)

        context_parts = []
        for i, fb in enumerate(relevant_feedbacks, 1):
            metadata = fb.get("metadata", {})
            product = metadata.get("product", "Unknown")
            user_id = metadata.get("user_id", "anonymous")
            timestamp = metadata.get("timestamp", "unknown")
            nps = metadata.get("nps_score", "N/A")
            categories = metadata.get("categories", [])
            cats_str = f" [{', '.join(categories)}]" if categories else ""
            context_parts.append(
                f"{i}. [Product: {product}] [NPS: {nps}]{cats_str} [User: {user_id}] [Time: {timestamp}]\n   Feedback: {fb.get('text', '')}"
            )

        context = "\n\n".join(context_parts) if context_parts else "No feedback entries matched your query. Here are all available feedbacks for analysis."
        product_context = f" focusing on product '{product_filter}'" if product_filter else ""

        prompt = f"""You are a product insights assistant helping a product manager analyze user feedback.

The product manager asks: "{user_message}"

--- USER FEEDBACK DATA{product_context} ---

{context}
{kb_context}

Based on this data, provide a concise response:
- Use bullet points and short paragraphs
- If knowledge base articles match, include relevant policies or procedures
- Focus on key insights and actionable takeaways
- Keep it brief and easy to scan

If there isn't enough information, say so briefly.

Response:"""

        response = self._call_llm([prompt])
        return response.content

    def generate_trend_analysis(self, trends_data: Dict[str, Any]) -> str:
        cats = trends_data.get("category_counts", {})
        total = trends_data.get("total_in_period", 0)
        avg_conf = trends_data.get("avg_confidence", 0)
        review_count = trends_data.get("needs_review_count", 0)
        daily = trends_data.get("daily_breakdown", {})

        top_cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)[:10]
        cats_text = "\n".join([f"  - {k}: {v} mentions" for k, v in top_cats])

        days_text = ""
        if daily:
            days_sorted = sorted(daily.items())
            for day, day_cats in days_sorted[-7:]:
                top = sorted(day_cats.items(), key=lambda x: x[1], reverse=True)[:3]
                top_str = ", ".join([f"{k}({v})" for k, v in top])
                days_text += f"  {day}: {top_str}\n"

        prompt = f"""You are a CX data analyst. Analyze these feedback trends from the past {trends_data.get('period_days', 7)} days.

TOTAL FEEDBACKS: {total}
AVG CONFIDENCE: {avg_conf}
ITEMS FLAGGED FOR REVIEW: {review_count}

TOP CATEGORIES THIS PERIOD:
{cats_text}

DAILY BREAKDOWN (last 7 days):
{days_text}

Provide a concise trend report:
1. What are the top 3 concerns this period?
2. Any notable changes or spikes compared to normal?
3. What should teams focus on?
4. Key metrics summary

Keep it brief and actionable."""

        try:
            response = self._call_llm([prompt])
            return response.content.strip()
        except Exception:
            return "Trend analysis is currently unavailable. Please check back later."

    def generate_team_report(self, team_name: str, feedbacks: List[Dict]) -> str:
        if not feedbacks:
            return f"No feedback items found for {team_name}."

        total = len(feedbacks)
        nps_scores = [f.get("metadata", {}).get("nps_score", 5) for f in feedbacks]
        avg_nps = round(sum(nps_scores) / len(nps_scores), 1) if nps_scores else 0
        promoters = sum(1 for s in nps_scores if s >= 9)
        detractors = sum(1 for s in nps_scores if s <= 6)

        items_text = ""
        for i, fb in enumerate(feedbacks[:15], 1):
            meta = fb.get("metadata", {})
            items_text += f"{i}. \"{fb.get('text', '')[:150]}\" [NPS: {meta.get('nps_score', '?')}] [Categories: {', '.join(meta.get('categories', []))}]\n"

        prompt = f"""You are a CX report writer. Generate a concise {team_name} report.

PERIOD SUMMARY:
- Total feedback items: {total}
- Average NPS: {avg_nps}
- Promoters (9-10): {promoters}
- Detractors (1-6): {detractors}

FEEDBACK ITEMS:
{items_text}

Generate a 3-paragraph report:
1. Executive summary of the feedback period
2. Key themes and patterns identified
3. Recommended actions for the team

Keep it concise and actionable. No more than 250 words."""

        try:
            response = self._call_llm([prompt])
            return response.content.strip()
        except Exception:
            return f"Report generation for {team_name} failed. Please try again."


llm_service = LLMService()
