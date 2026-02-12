"""Cryptographic primitives and envelope encryption for BigHeads.

This module implements:
- Group-key encryption for broadcast payloads.
- A prototype Noise NN-like setup handshake for private chats.
- Per-message derived keys for private chats, authenticated with ChaCha20-Poly1305.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from utils.helpers import from_b64, to_b64


def _hkdf(input_key: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        info=info,
    ).derive(input_key)


@dataclass(slots=True)
class ChatSession:
    """Material for decrypting and encrypting private chat messages."""

    local_priv_b64: str
    peer_pub_b64: str


class CryptoManager:
    def __init__(self, group_passphrase: str) -> None:
        self.group_passphrase = group_passphrase

    def _group_key(self) -> bytes:
        seed = hashlib.sha256(self.group_passphrase.encode("utf-8")).digest()
        return _hkdf(seed, b"bigheads-group", b"group-key")

    def update_group_passphrase(self, passphrase: str) -> None:
        self.group_passphrase = passphrase

    def encrypt_group(self, plaintext: bytes, aad: bytes = b"") -> dict[str, str]:
        key = self._group_key()
        nonce = os.urandom(12)
        cipher = ChaCha20Poly1305(key)
        ciphertext = cipher.encrypt(nonce, plaintext, aad)
        return {"nonce": to_b64(nonce), "ct": to_b64(ciphertext)}

    def decrypt_group(self, payload: dict[str, str], aad: bytes = b"") -> bytes:
        key = self._group_key()
        nonce = from_b64(payload["nonce"])
        ct = from_b64(payload["ct"])
        cipher = ChaCha20Poly1305(key)
        return cipher.decrypt(nonce, ct, aad)

    def start_noise_nn(self) -> tuple[str, x25519.X25519PrivateKey]:
        """Initiator creates ephemeral key and sends its public key."""
        priv = x25519.X25519PrivateKey.generate()
        pub = priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return to_b64(pub), priv

    def respond_noise_nn(self, initiator_pub_b64: str) -> tuple[dict[str, str], ChatSession]:
        """Responder processes init pub, returns response payload and session material."""
        responder_priv = x25519.X25519PrivateKey.generate()
        responder_pub = responder_priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        initiator_pub = x25519.X25519PublicKey.from_public_bytes(from_b64(initiator_pub_b64))
        # Establish a session private/public pair from the handshake.
        session = ChatSession(
            local_priv_b64=to_b64(
                responder_priv.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            ),
            peer_pub_b64=initiator_pub_b64,
        )
        return ({"noise": "nn_resp", "pub": to_b64(responder_pub)}, session)

    def finalize_noise_nn(self, initiator_priv: x25519.X25519PrivateKey, responder_pub_b64: str) -> ChatSession:
        """Initiator stores a session from its handshake private key and responder pub."""
        return ChatSession(
            local_priv_b64=to_b64(
                initiator_priv.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            ),
            peer_pub_b64=responder_pub_b64,
        )

    def encrypt_private(
        self,
        plaintext: bytes,
        chat_id: str,
        msg_id: str,
        session: ChatSession,
        aad: bytes = b"",
    ) -> dict[str, str]:
        """Encrypt with per-message ephemeral key + session static pub.

        Receiver derives the same shared secret using its session private key and the
        message ephemeral public key. The final AEAD key is HKDF(shared, salt, info).
        """
        msg_eph_priv = x25519.X25519PrivateKey.generate()
        msg_eph_pub = msg_eph_priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        peer_pub = x25519.X25519PublicKey.from_public_bytes(from_b64(session.peer_pub_b64))
        shared = msg_eph_priv.exchange(peer_pub)
        salt = os.urandom(16)
        key = _hkdf(shared, salt, f"bigheads-private:{chat_id}:{msg_id}".encode("utf-8"))
        nonce = os.urandom(12)
        ct = ChaCha20Poly1305(key).encrypt(nonce, plaintext, aad)
        return {
            "nonce": to_b64(nonce),
            "ct": to_b64(ct),
            "salt": to_b64(salt),
            "eph_pub": to_b64(msg_eph_pub),
        }

    def decrypt_private(
        self,
        payload: dict[str, str],
        chat_id: str,
        msg_id: str,
        session: ChatSession,
        aad: bytes = b"",
    ) -> bytes:
        local_priv = x25519.X25519PrivateKey.from_private_bytes(from_b64(session.local_priv_b64))
        msg_eph_pub = x25519.X25519PublicKey.from_public_bytes(from_b64(payload["eph_pub"]))
        shared = local_priv.exchange(msg_eph_pub)
        key = _hkdf(shared, from_b64(payload["salt"]), f"bigheads-private:{chat_id}:{msg_id}".encode("utf-8"))
        return ChaCha20Poly1305(key).decrypt(
            from_b64(payload["nonce"]),
            from_b64(payload["ct"]),
            aad,
        )

    @staticmethod
    def session_to_dict(session: ChatSession) -> dict[str, Any]:
        return {"local_priv_b64": session.local_priv_b64, "peer_pub_b64": session.peer_pub_b64}

    @staticmethod
    def session_from_dict(data: dict[str, Any]) -> ChatSession:
        return ChatSession(local_priv_b64=data["local_priv_b64"], peer_pub_b64=data["peer_pub_b64"])
