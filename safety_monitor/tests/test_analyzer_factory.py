"""Factory name routing for OAS external security analyzers. No HF/GPU."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from safety_monitor.adapters.factory import (
    create_external_analyzer,
    normalize_analyzer_name,
)


def test_normalize_analyzer_name():
    assert normalize_analyzer_name("Shield_Gemma") == "shield-gemma"
    assert normalize_analyzer_name(" QWEN ") == "qwen"


def test_unknown_name_errors():
    with pytest.raises(ValueError, match="Unknown security analyzer"):
        create_external_analyzer("llama-guard")
    with pytest.raises(ValueError, match="Unknown security analyzer"):
        create_external_analyzer("none")


def test_qwen_routes_to_loader(monkeypatch):
    critic = object()
    analyzer = object()
    loader = MagicMock(return_value=critic)
    wrapper = MagicMock(return_value=analyzer)
    monkeypatch.setattr("safety_monitor.critic.qwen.load_qwen_critic", loader)
    monkeypatch.setattr(
        "safety_monitor.adapters.openhands.as_openhands_analyzer", wrapper
    )
    out = create_external_analyzer("qwen", qwen_model_path="/models/qwen")
    loader.assert_called_once()
    wrapper.assert_called_once_with(critic)
    assert out is analyzer


def test_shieldgemma_aliases_route(monkeypatch):
    critic = object()
    analyzer = object()
    loader = MagicMock(return_value=critic)
    wrapper = MagicMock(return_value=analyzer)
    monkeypatch.setattr(
        "safety_monitor.critic.shieldgemma.load_shieldgemma_critic", loader
    )
    monkeypatch.setattr(
        "safety_monitor.adapters.openhands.as_openhands_analyzer", wrapper
    )
    for name in ("shieldgemma", "shield-gemma", "shield_gemma"):
        loader.reset_mock()
        wrapper.reset_mock()
        out = create_external_analyzer(name, shieldgemma_model_path="/models/sg")
        loader.assert_called_once()
        wrapper.assert_called_once_with(critic)
        assert out is analyzer
