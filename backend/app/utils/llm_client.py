"""
LLM客户端封装
支持 OpenAI 格式 (Ollama / OpenAI) 和 Anthropic Claude
根据模型名称自动选择后端
"""

import json
import os
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config


class LLMClient:
    """LLM客户端 — 支持 OpenAI-compatible 和 Anthropic"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME

        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")

        self._timeout = timeout
        self._anthropic_client = None
        self._openai_client = None

        # Ollama context window size — prevents prompt truncation.
        self._num_ctx = int(os.environ.get('OLLAMA_NUM_CTX', '8192'))

    def _is_anthropic(self) -> bool:
        """Check if we're using an Anthropic Claude model."""
        return (self.model or '').startswith('claude')

    def _is_ollama(self) -> bool:
        """Check if we're talking to an Ollama server."""
        return '11434' in (self.base_url or '')

    def _get_anthropic_client(self):
        """Lazy-init Anthropic client."""
        if self._anthropic_client is None:
            import anthropic
            self._anthropic_client = anthropic.Anthropic(
                api_key=self.api_key,
                timeout=self._timeout,
            )
        return self._anthropic_client

    def _get_openai_client(self):
        """Lazy-init OpenAI client."""
        if self._openai_client is None:
            self._openai_client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self._timeout,
            )
        return self._openai_client

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）

        Returns:
            模型响应文本
        """
        if self._is_anthropic():
            return self._chat_anthropic(messages, temperature, max_tokens, response_format)
        return self._chat_openai(messages, temperature, max_tokens, response_format)

    def _chat_anthropic(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict] = None
    ) -> str:
        """Send chat request via Anthropic SDK."""
        client = self._get_anthropic_client()

        # Extract system message (Anthropic uses a separate system param)
        system = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = (system + "\n\n" + msg["content"]) if system else msg["content"]
            else:
                user_messages.append(msg)

        # If response_format is JSON, add instruction to system prompt
        if response_format and response_format.get("type") == "json_object":
            json_instruction = "\n\nIMPORTANT: You must respond with valid JSON only. No markdown, no explanation, just the JSON object."
            system = (system + json_instruction) if system else json_instruction

        kwargs = {
            "model": self.model,
            "messages": user_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        # Remove <think> tags from some models
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content

    def _chat_openai(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict] = None
    ) -> str:
        """Send chat request via OpenAI SDK."""
        client = self._get_openai_client()

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        # For Ollama: pass num_ctx via extra_body to prevent prompt truncation
        if self._is_ollama() and self._num_ctx:
            kwargs["extra_body"] = {
                "options": {"num_ctx": self._num_ctx}
            }

        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # 部分模型会在content中包含<think>思考内容，需要移除
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            解析后的JSON对象
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        # 清理markdown代码块标记
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"LLM返回的JSON格式无效: {cleaned_response}")
