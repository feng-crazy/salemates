# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""E-Signature client integration stub.

This module provides a stub implementation for e-signature service
integration, supporting platforms like DocuSign, 法大大, etc.

Example:
    >>> from salemates.integrations.esignature import ESignatureClient
    >>> client = ESignatureClient(provider="docusign")
    >>> result = await client.send_for_signature(contract_id, signers)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class SignatureProvider(str, Enum):
    """Supported e-signature providers."""

    DOCUSIGN = "docusign"
    FADADA = "fadada"  # 法大大
    SIGNNOW = "signnow"
    ADOBE_SIGN = "adobe_sign"


class SignatureStatus(str, Enum):
    """Status of a signature request."""

    DRAFT = "draft"
    SENT = "sent"
    SIGNED = "signed"
    COMPLETED = "completed"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class Signer:
    """Signer information for e-signature.

    Attributes:
        name: Signer's full name.
        email: Signer's email address.
        role: Role of the signer (e.g., "signer", "cc", "approver").
        order: Signing order (for sequential signing).
        signed_at: Timestamp when signed.
        status: Current signing status.
    """

    name: str
    email: str
    role: str = "signer"
    order: int = 1
    signed_at: Optional[datetime] = None
    status: str = "pending"


@dataclass
class SignatureRequest:
    """E-signature request details.

    Attributes:
        request_id: Unique identifier for the request.
        contract_id: Reference to the contract being signed.
        title: Title of the document.
        signers: List of signers.
        status: Current status of the request.
        created_at: Creation timestamp.
        expires_at: Expiration timestamp.
        completed_at: Completion timestamp.
        document_url: URL to the signed document.
        metadata: Additional metadata.
    """

    request_id: str
    contract_id: str
    title: str
    signers: list[Signer]
    status: SignatureStatus = SignatureStatus.DRAFT
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    document_url: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SignatureResult:
    """Result of a signature operation.

    Attributes:
        success: Whether the operation succeeded.
        request_id: ID of the signature request.
        signing_url: URL for signers to access the document.
        message: Status message.
        error: Error message if failed.
    """

    success: bool
    request_id: Optional[str] = None
    signing_url: Optional[str] = None
    message: str = ""
    error: Optional[str] = None


class ESignatureClient:
    """Client for e-signature service integration.

    This is a stub implementation that can be extended to support
    various e-signature providers like DocuSign, 法大大, etc.

    Attributes:
        provider: The e-signature provider being used.
        api_key: API key for authentication.
        api_base: Base URL for the provider's API.
    """

    def __init__(
        self,
        provider: SignatureProvider | str = SignatureProvider.DOCUSIGN,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        """Initialize the e-signature client.

        Args:
            provider: E-signature provider to use.
            api_key: API key for authentication.
            api_base: Base URL for the API (optional override).
        """
        if isinstance(provider, str):
            provider = SignatureProvider(provider)
        self.provider = provider
        self._api_key = api_key
        self._api_base = api_base or self._get_default_base_url()

    def _get_default_base_url(self) -> str:
        """Get default API base URL for the provider."""
        urls = {
            SignatureProvider.DOCUSIGN: "https://demo.docusign.net/restapi",
            SignatureProvider.FADADA: "https://api.fadada.com",
            SignatureProvider.SIGNNOW: "https://api.signnow.com",
            SignatureProvider.ADOBE_SIGN: "https://api.na1.adobesign.com",
        }
        return urls.get(self.provider, "")

    async def send_for_signature(
        self,
        contract_id: str,
        contract_text: str,
        title: str,
        signers: list[Signer],
        expires_in_days: int = 30,
        metadata: Optional[dict[str, Any]] = None,
    ) -> SignatureResult:
        """Send a contract for e-signature.

        This is a stub implementation. In production, this would
        integrate with the actual e-signature provider's API.

        Args:
            contract_id: Contract identifier.
            contract_text: Full contract text/document.
            title: Document title.
            signers: List of signers.
            expires_in_days: Days until the request expires.
            metadata: Additional metadata.

        Returns:
            SignatureResult with the outcome.
        """
        import uuid

        request_id = f"SIG-{uuid.uuid4().hex[:8].upper()}"

        return SignatureResult(
            success=True,
            request_id=request_id,
            signing_url=f"https://sign.example.com/request/{request_id}",
            message=f"Signature request created successfully via {self.provider.value}. "
            f"This is a stub - integrate with {self.provider.value} API for production use.",
        )

    async def get_signature_status(self, request_id: str) -> Optional[SignatureRequest]:
        """Get the status of a signature request.

        This is a stub implementation.

        Args:
            request_id: The signature request ID.

        Returns:
            SignatureRequest if found, None otherwise.
        """
        return SignatureRequest(
            request_id=request_id,
            contract_id="CTR-STUB",
            title="Stub Document",
            signers=[Signer(name="Stub Signer", email="stub@example.com")],
            status=SignatureStatus.SENT,
            created_at=datetime.utcnow(),
            message="This is a stub response - integrate with API for production use.",
        )

    async def cancel_signature_request(self, request_id: str) -> bool:
        """Cancel a signature request.

        This is a stub implementation.

        Args:
            request_id: The signature request ID.

        Returns:
            True if cancelled successfully.
        """
        return True

    async def download_signed_document(self, request_id: str) -> Optional[bytes]:
        """Download the signed document.

        This is a stub implementation.

        Args:
            request_id: The signature request ID.

        Returns:
            Document bytes if available, None otherwise.
        """
        return None

    def get_signing_url(self, request_id: str, signer_email: str) -> Optional[str]:
        """Get the signing URL for a specific signer.

        Args:
            request_id: The signature request ID.
            signer_email: Email of the signer.

        Returns:
            Signing URL if available.
        """
        return f"https://sign.example.com/request/{request_id}?signer={signer_email}"
