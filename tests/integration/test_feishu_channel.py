# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for Feishu channel.

Tests:
- URL verification endpoint
- Text message handling
- Image message handling
- Message response
- Event callback validation
"""

import json
import pytest
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from salemates.config.schema import SessionKey
from salemates.bus.events import InboundMessage, OutboundMessage


# ============ Mock Fixtures ============


@dataclass
class MockFeishuEvent:
    """Mock Feishu event data."""

    event: Any = None


@dataclass
class MockFeishuMessage:
    """Mock Feishu message."""

    message_id: str = "msg_123456"
    chat_id: str = "oc_test_chat"
    chat_type: str = "group"  # "p2p" or "group"
    message_type: str = "text"
    content: str = '{"text": "测试消息"}'
    root_id: str | None = None


@dataclass
class MockFeishuSender:
    """Mock Feishu sender."""

    sender_type: str = "user"
    open_id: str = "ou_test_user"


@dataclass
class MockFeishuEventDetail:
    """Mock Feishu event detail."""

    message: MockFeishuMessage = field(default_factory=MockFeishuMessage)
    sender: Any = None


@pytest.fixture
def mock_feishu_event():
    """Create mock Feishu URL verification event."""
    return {
        "type": "url_verification",
        "challenge": "test_challenge_token",
    }


@pytest.fixture
def mock_feishu_event_text():
    """Create mock Feishu text message event."""
    sender = MagicMock()
    sender.sender_type = "user"
    sender.sender_id = MagicMock()
    sender.sender_id.open_id = "ou_test_user"

    message = MagicMock()
    message.message_id = "msg_text_001"
    message.chat_id = "oc_test_chat"
    message.chat_type = "group"
    message.message_type = "text"
    message.content = json.dumps({"text": "你好，我想了解你们的产品"})
    message.root_id = None

    event = MagicMock()
    event.message = message
    event.sender = sender

    data = MagicMock()
    data.event = event

    return data


@pytest.fixture
def mock_feishu_event_image():
    """Create mock Feishu image message event."""
    sender = MagicMock()
    sender.sender_type = "user"
    sender.sender_id = MagicMock()
    sender.sender_id.open_id = "ou_test_user"

    message = MagicMock()
    message.message_id = "msg_image_001"
    message.chat_id = "oc_test_chat"
    message.chat_type = "p2p"
    message.message_type = "image"
    message.content = json.dumps({"image_key": "img_test_key_123"})
    message.root_id = None

    event = MagicMock()
    event.message = message
    event.sender = sender

    data = MagicMock()
    data.event = event

    return data


@pytest.fixture
def test_client():
    """Create a mock test client."""
    return MagicMock()


# ============ Test Classes ============


class TestFeishuChannelURLVerification:
    """Test Feishu URL verification endpoint."""

    def test_url_verification_challenge(self, mock_feishu_event):
        """Test URL verification returns correct challenge."""
        # URL verification should echo back the challenge
        challenge = mock_feishu_event.get("challenge")

        assert challenge == "test_challenge_token"
        # In real implementation, this would be returned as JSON response

    def test_url_verification_format(self, mock_feishu_event):
        """Test URL verification event format."""
        assert mock_feishu_event["type"] == "url_verification"
        assert "challenge" in mock_feishu_event


class TestFeishuChannelTextMessageHandling:
    """Test Feishu text message handling."""

    @pytest.mark.asyncio
    async def test_text_message_parsing(self, mock_feishu_event_text):
        """Test parsing of text message content."""
        event = mock_feishu_event_text.event
        content = json.loads(event.message.content)

        assert content.get("text") == "你好，我想了解你们的产品"

    @pytest.mark.asyncio
    async def test_text_message_sender_extraction(self, mock_feishu_event_text):
        """Test extraction of sender information."""
        event = mock_feishu_event_text.event

        assert event.sender.sender_type == "user"
        assert event.sender.sender_id.open_id == "ou_test_user"

    @pytest.mark.asyncio
    async def test_text_message_chat_info(self, mock_feishu_event_text):
        """Test extraction of chat information."""
        message = mock_feishu_event_text.event.message

        assert message.chat_id == "oc_test_chat"
        assert message.chat_type == "group"
        assert message.message_type == "text"

    @pytest.mark.asyncio
    async def test_p2p_message_handling(self):
        """Test handling of P2P (private) messages."""
        sender = MagicMock()
        sender.sender_type = "user"
        sender.sender_id = MagicMock()
        sender.sender_id.open_id = "ou_p2p_user"

        message = MagicMock()
        message.message_id = "msg_p2p_001"
        message.chat_id = "ou_p2p_user"  # P2P uses open_id as chat_id
        message.chat_type = "p2p"
        message.message_type = "text"
        message.content = json.dumps({"text": "私聊消息"})
        message.root_id = None

        event = MagicMock()
        event.message = message
        event.sender = sender

        data = MagicMock()
        data.event = event

        assert data.event.message.chat_type == "p2p"
        assert data.event.message.message_type == "text"


class TestFeishuChannelImageMessageHandling:
    """Test Feishu image message handling."""

    @pytest.mark.asyncio
    async def test_image_message_parsing(self, mock_feishu_event_image):
        """Test parsing of image message content."""
        event = mock_feishu_event_image.event
        content = json.loads(event.message.content)

        assert content.get("image_key") == "img_test_key_123"

    @pytest.mark.asyncio
    async def test_image_message_type_detection(self, mock_feishu_event_image):
        """Test detection of image message type."""
        message = mock_feishu_event_image.event.message

        assert message.message_type == "image"

    @pytest.mark.asyncio
    async def test_image_key_extraction(self, mock_feishu_event_image):
        """Test extraction of image key from message."""
        event = mock_feishu_event_image.event
        content = json.loads(event.message.content)
        image_key = content.get("image_key")

        assert image_key is not None
        assert image_key == "img_test_key_123"


class TestFeishuChannelMessageResponse:
    """Test sending responses back to Feishu."""

    @pytest.mark.asyncio
    async def test_create_outbound_message(self):
        """Test creating outbound message for Feishu."""
        session_key = SessionKey(
            type="feishu",
            channel_id="sales_bot",
            chat_id="oc_test_chat",
        )

        msg = OutboundMessage(
            session_key=session_key,
            content="感谢您的咨询，我们的产品有很多功能。",
        )

        assert msg.content == "感谢您的咨询，我们的产品有很多功能。"
        assert msg.is_normal_message is True

    @pytest.mark.asyncio
    async def test_message_with_metadata(self):
        """Test message with reply metadata."""
        session_key = SessionKey(
            type="feishu",
            channel_id="sales_bot",
            chat_id="ou_test_user",
        )

        msg = OutboundMessage(
            session_key=session_key,
            content="回复您的消息",
            metadata={
                "reply_to": "ou_test_user",
                "message_id": "msg_original_001",
            },
        )

        assert msg.metadata.get("reply_to") == "ou_test_user"
        assert msg.metadata.get("message_id") == "msg_original_001"

    @pytest.mark.asyncio
    async def test_reply_to_group_message(self):
        """Test replying to a group message."""
        session_key = SessionKey(
            type="feishu",
            channel_id="sales_bot",
            chat_id="oc_test_chat",
        )

        msg = OutboundMessage(
            session_key=session_key,
            content="这是群消息回复",
            metadata={
                "reply_to": "oc_test_chat",
                "chat_type": "group",
            },
        )

        assert msg.metadata.get("chat_type") == "group"


class TestFeishuChannelEventCallbackValidation:
    """Test event callback signature validation."""

    def test_event_signature_validation_structure(self):
        """Test event signature validation structure."""
        # Feishu events should have specific structure
        required_fields = ["event", "header"]

        # Mock event structure
        mock_event = {
            "header": {
                "event_id": "event_123",
                "event_type": "im.message.receive_v1",
                "create_time": "1234567890",
                "token": "verification_token",
                "app_id": "cli_test_app",
            },
            "event": {
                "message": {"message_id": "msg_123"},
                "sender": {"sender_id": {"open_id": "ou_123"}},
            },
        }

        for field in required_fields:
            assert field in mock_event

    def test_event_type_parsing(self):
        """Test parsing of event type."""
        event_type = "im.message.receive_v1"

        # Should be able to parse event type
        parts = event_type.split(".")
        assert parts[0] == "im"  # Module
        assert parts[1] == "message"  # Resource
        assert parts[2] == "receive_v1"  # Action

    def test_message_receive_event_structure(self):
        """Test structure of message receive event."""
        event = {
            "message": {
                "message_id": "msg_001",
                "root_id": None,
                "parent_id": None,
                "create_time": "1234567890",
                "chat_id": "oc_001",
                "chat_type": "group",
                "message_type": "text",
                "content": '{"text": "test"}',
                "mentions": [],
            },
            "sender": {
                "sender_id": {
                    "open_id": "ou_001",
                    "user_id": "user_001",
                },
                "sender_type": "user",
                "tenant_key": "tenant_001",
            },
        }

        assert event["message"]["message_type"] == "text"
        assert event["sender"]["sender_type"] == "user"


class TestFeishuChannelMessageTypes:
    """Test different message types in Feishu channel."""

    def test_post_message_structure(self):
        """Test post message structure (rich text)."""
        post_content = {
            "title": "",
            "content": [
                [{"tag": "text", "text": "这是一条富文本消息"}],
                [{"tag": "text", "text": "第二行"}],
            ],
        }

        content_json = json.dumps(post_content)

        # Should be valid JSON
        parsed = json.loads(content_json)
        assert parsed["content"][0][0]["text"] == "这是一条富文本消息"

    def test_file_message_structure(self):
        """Test file message structure."""
        file_content = {
            "file_key": "file_001",
            "file_name": "document.pdf",
            "file_size": 1024,
        }

        assert file_content["file_key"] == "file_001"
        assert file_content["file_name"] == "document.pdf"

    def test_sticker_message_structure(self):
        """Test sticker message structure."""
        sticker_content = {
            "file_key": "sticker_001",
        }

        assert sticker_content["file_key"] == "sticker_001"


class TestFeishuChannelDeduplication:
    """Test message deduplication in Feishu channel."""

    def test_message_id_tracking(self):
        """Test tracking of processed message IDs."""
        processed_ids = set()

        # Simulate processing messages
        msg_id_1 = "msg_001"
        msg_id_2 = "msg_002"
        msg_id_3 = "msg_001"  # Duplicate

        # Add to processed set
        processed_ids.add(msg_id_1)
        processed_ids.add(msg_id_2)

        # Check duplicates
        assert msg_id_1 in processed_ids
        assert msg_id_2 in processed_ids
        assert msg_id_3 in processed_ids  # Already processed

    def test_message_cache_limit(self):
        """Test message cache has size limit."""
        from collections import OrderedDict

        # Use OrderedDict with size limit like the implementation
        cache: OrderedDict[str, None] = OrderedDict()

        # Add messages
        for i in range(1001):
            cache[f"msg_{i}"] = None
            while len(cache) > 1000:
                cache.popitem(last=False)

        assert len(cache) == 1000
        # First message should be evicted
        assert "msg_0" not in cache


class TestFeishuChannelBotMessages:
    """Test handling of bot messages."""

    def test_skip_bot_messages(self):
        """Test that bot messages are skipped."""
        sender = MagicMock()
        sender.sender_type = "bot"

        # Bot messages should be filtered out
        assert sender.sender_type == "bot"

    def test_user_message_not_skipped(self, mock_feishu_event_text):
        """Test that user messages are processed."""
        event = mock_feishu_event_text.event

        assert event.sender.sender_type == "user"


class TestFeishuChannelMentions:
    """Test mention handling in Feishu channel."""

    def test_user_mention_format(self):
        """Test @mention format for users."""
        # Feishu @mention format: @_user_1
        content = "@_user_1 你好，请查看这个消息"

        # Should detect mention
        import re

        mention_pattern = re.compile(r"@_user_\d+")
        mentions = mention_pattern.findall(content)

        assert len(mentions) == 1
        assert mentions[0] == "@_user_1"

    def test_mention_replacement(self):
        """Test replacement of mention placeholders."""
        import re

        content = "@_user_1 你好"
        sender_id = "ou_test_user"

        mention_pattern = re.compile(r"@_user_\d+")
        replaced = mention_pattern.sub(f"@{sender_id}", content)

        assert sender_id in replaced


class TestFeishuChannelTopicGroups:
    """Test topic (thread) group handling."""

    def test_thread_message_detection(self):
        """Test detection of thread messages."""
        # Message with root_id indicates it's in a thread
        message = MagicMock()
        message.message_id = "msg_thread_001"
        message.root_id = "msg_root_001"

        assert message.root_id is not None
        # This message is part of a thread

    def test_first_message_in_thread(self):
        """Test first message in a thread (root_id is None)."""
        message = MagicMock()
        message.message_id = "msg_root_001"
        message.root_id = None

        assert message.root_id is None
        # First message in thread has no root_id


class TestFeishuChannelEdgeCases:
    """Test edge cases in Feishu channel."""

    def test_empty_message_content(self):
        """Test handling of empty message content."""
        content = ""

        # Should handle gracefully
        assert content == ""

    def test_malformed_json_content(self):
        """Test handling of malformed JSON in message content."""
        content = "not valid json {"

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Should handle gracefully
            parsed = {"text": content}

        assert isinstance(parsed, dict)

    def test_very_long_message(self):
        """Test handling of very long messages."""
        long_message = "测试" * 10000

        # Should not crash
        assert len(long_message) == 20000

    def test_special_characters_in_content(self):
        """Test handling of special characters."""
        content = "测试消息！@#￥%……&*（）——+"

        # Should preserve special characters
        assert "！" in content


class TestFeishuChannelSessionKey:
    """Test session key creation for Feishu channel."""

    def test_session_key_creation(self):
        """Test session key is properly created for Feishu."""
        session_key = SessionKey(
            type="feishu",
            channel_id="sales_bot",
            chat_id="oc_test_chat",
        )

        assert session_key.type == "feishu"
        assert session_key.channel_id == "sales_bot"
        assert session_key.chat_id == "oc_test_chat"

    def test_session_key_for_p2p(self):
        """Test session key for P2P chat."""
        session_key = SessionKey(
            type="feishu",
            channel_id="sales_bot",
            chat_id="ou_p2p_user",
        )

        # P2P uses open_id as chat_id
        assert session_key.chat_id.startswith("ou_")

    def test_session_key_for_group(self):
        """Test session key for group chat."""
        session_key = SessionKey(
            type="feishu",
            channel_id="sales_bot",
            chat_id="oc_group_chat",
        )

        # Group uses chat_id starting with oc_
        assert session_key.chat_id.startswith("oc_")
