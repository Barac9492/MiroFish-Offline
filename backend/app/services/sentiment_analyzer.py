"""
Sentiment Analyzer — parses simulation actions and classifies stance toward market question
"""

import os
import json
from typing import List, Dict, Any, Optional

from ..config import Config
from ..models.prediction import SentimentResult
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger('mirofish.sentiment_analyzer')

CLASSIFY_SYSTEM_PROMPT = """You are analyzing social media posts from a simulation about a prediction market question.

For each post, classify the author's stance:
- "for": supports the YES outcome
- "against": supports the NO outcome
- "neutral": no clear position or purely informational

Also rate confidence (0.0-1.0) in your classification.

Return JSON array:
[
    {"post_index": 0, "stance": "for", "confidence": 0.8, "key_argument": "brief summary"},
    ...
]

Be precise. Only classify as "for" or "against" if the post clearly takes a side."""


class SentimentAnalyzer:
    """Analyzes simulation output to estimate probability"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    def analyze(
        self,
        simulation_id: str,
        market_question: str,
        platform: str = "reddit",
    ) -> SentimentResult:
        """
        Analyze simulation actions to compute simulated probability.

        Args:
            simulation_id: ID of completed simulation
            market_question: The original prediction market question
            platform: Which platform's actions to analyze

        Returns:
            SentimentResult with probability and breakdown
        """
        # Load posts from actions.jsonl
        posts = self._load_posts(simulation_id, platform)

        if not posts:
            logger.warning(f"No posts found for simulation {simulation_id}")
            return SentimentResult(
                simulated_probability=0.5,
                confidence=0.0,
                stance_counts={"for": 0, "against": 0, "neutral": 0},
                key_arguments_for=[],
                key_arguments_against=[],
                total_posts_analyzed=0,
            )

        logger.info(f"Analyzing {len(posts)} posts for simulation {simulation_id}")

        # Batch-classify posts via LLM
        all_classifications = []
        batch_size = 15

        for i in range(0, len(posts), batch_size):
            batch = posts[i:i + batch_size]
            classifications = self._classify_batch(batch, market_question, start_index=i)
            all_classifications.extend(classifications)

        # Compute weighted probability
        return self._compute_result(all_classifications, len(posts))

    def _load_posts(self, simulation_id: str, platform: str) -> List[Dict[str, Any]]:
        """Load CREATE_POST and CREATE_COMMENT actions from actions.jsonl"""
        actions_path = os.path.join(
            Config.OASIS_SIMULATION_DATA_DIR,
            simulation_id,
            platform,
            'actions.jsonl'
        )

        if not os.path.exists(actions_path):
            logger.warning(f"Actions file not found: {actions_path}")
            return []

        posts = []
        with open(actions_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    action = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Skip event records
                if 'event_type' in action:
                    continue

                action_type = action.get('action_type', '')
                if action_type not in ('CREATE_POST', 'CREATE_COMMENT'):
                    continue

                content = ''
                args = action.get('action_args', {})
                if isinstance(args, dict):
                    content = args.get('content', '')
                elif isinstance(args, str):
                    content = args

                if not content or len(content) < 10:
                    continue

                posts.append({
                    "agent_name": action.get('agent_name', 'Unknown'),
                    "action_type": action_type,
                    "content": content[:500],  # Truncate long posts
                    "round": action.get('round', 0),
                })

        return posts

    def _classify_batch(
        self,
        posts: List[Dict[str, Any]],
        market_question: str,
        start_index: int = 0,
    ) -> List[Dict[str, Any]]:
        """Classify a batch of posts via LLM"""
        posts_text = []
        for i, post in enumerate(posts):
            posts_text.append(
                f"[Post {start_index + i}] ({post['agent_name']}, {post['action_type']}):\n"
                f"{post['content']}"
            )

        user_message = (
            f"# Prediction Market Question\n{market_question}\n\n"
            f"# Posts to Classify\n" + "\n\n".join(posts_text)
        )

        messages = [
            {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        try:
            result = self.llm_client.chat_json(
                messages=messages,
                temperature=0.2,
                max_tokens=4096,
            )

            if isinstance(result, list):
                return result
            if isinstance(result, dict) and 'classifications' in result:
                return result['classifications']
            return []

        except Exception as e:
            logger.error(f"Failed to classify batch: {e}")
            return []

    def _compute_result(
        self,
        classifications: List[Dict[str, Any]],
        total_posts: int,
    ) -> SentimentResult:
        """Compute probability from classifications"""
        stance_counts = {"for": 0, "against": 0, "neutral": 0}
        weighted_for = 0.0
        weighted_against = 0.0
        weighted_total = 0.0
        args_for = []
        args_against = []

        for c in classifications:
            stance = c.get('stance', 'neutral')
            confidence = float(c.get('confidence', 0.5))
            key_arg = c.get('key_argument', '')

            if stance in stance_counts:
                stance_counts[stance] += 1
            else:
                stance_counts['neutral'] += 1
                stance = 'neutral'

            if stance == 'for':
                weighted_for += confidence
                weighted_total += confidence
                if key_arg:
                    args_for.append(key_arg)
            elif stance == 'against':
                weighted_against += confidence
                weighted_total += confidence
                if key_arg:
                    args_against.append(key_arg)
            else:
                weighted_total += confidence * 0.5  # Neutral contributes less

        # P(Yes) = weighted_for / weighted_total
        if weighted_total > 0:
            simulated_prob = weighted_for / (weighted_for + weighted_against) if (weighted_for + weighted_against) > 0 else 0.5
        else:
            simulated_prob = 0.5

        # Confidence based on sample size and agreement
        total_classified = stance_counts['for'] + stance_counts['against']
        if total_classified > 0:
            agreement = max(stance_counts['for'], stance_counts['against']) / total_classified
            sample_factor = min(total_classified / 20, 1.0)  # Full confidence at 20+ opinionated posts
            result_confidence = agreement * sample_factor
        else:
            result_confidence = 0.0

        # Deduplicate arguments (keep top 5)
        seen_for = set()
        unique_for = []
        for arg in args_for:
            key = arg.lower()[:50]
            if key not in seen_for:
                seen_for.add(key)
                unique_for.append(arg)

        seen_against = set()
        unique_against = []
        for arg in args_against:
            key = arg.lower()[:50]
            if key not in seen_against:
                seen_against.add(key)
                unique_against.append(arg)

        return SentimentResult(
            simulated_probability=simulated_prob,
            confidence=result_confidence,
            stance_counts=stance_counts,
            key_arguments_for=unique_for[:5],
            key_arguments_against=unique_against[:5],
            total_posts_analyzed=total_posts,
        )
