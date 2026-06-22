from content_engine.config import Config
from content_engine.llm import completer_for_role, extract_json


def _cfg(**providers):
    return Config({
        "providers": providers,
        "roles": {
            "scene_planning": {"primary": "anthropic", "fallback": "nim"},
            "qc": {"primary": "gemini", "fallback": "nim"},
        },
    })


def test_role_resolves_to_primary_when_keyed():
    cfg = _cfg(anthropic={"api_key": "sk-x", "model": "m"},
              nim={"api_key": "nk", "models": {"planner": "glm"}})
    name, pcfg = cfg.provider_for_role("scene_planning")
    assert name == "anthropic"
    assert pcfg["model"] == "m"


def test_role_falls_back_when_primary_unkeyed():
    cfg = _cfg(anthropic={"api_key": "", "model": "m"},
              nim={"api_key": "nk", "models": {"planner": "glm"}})
    name, _ = cfg.provider_for_role("scene_planning")
    assert name == "nim"


def test_role_returns_none_with_no_keys():
    cfg = _cfg(anthropic={"api_key": ""}, nim={"api_key": ""})
    name, _ = cfg.provider_for_role("scene_planning")
    assert name is None
    assert completer_for_role(cfg, "scene_planning") is None


def test_model_for_role_picks_nim_role_model():
    cfg = _cfg(nim={"api_key": "nk", "models": {"planner": "glm", "qc": "ds"}})
    assert cfg.model_for_role("nim", "scene_planning") == "glm"
    assert cfg.model_for_role("nim", "qc") == "ds"


def test_completer_built_when_keyed():
    cfg = _cfg(anthropic={"api_key": "sk-x", "model": "m",
                          "base_url": "https://example.test"})
    fn = completer_for_role(cfg, "scene_planning")
    assert callable(fn)
    assert fn.provider_name == "anthropic"


def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert extract_json('Here you go:\n{"a": 3}\nthanks') == {"a": 3}
    assert extract_json('[1, 2, 3]') == [1, 2, 3]
