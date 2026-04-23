from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_native_tools: bool = False
    supports_json_schema: bool = False
    supports_beta_parse: bool = False
    supports_streaming: bool = False
