from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace


def _make_skill(root: Path, name: str) -> Path:
    skill_dir = root / "product-knowledge" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        f"name: {name}\n"
        f"description: {name}\n"
        "---\n"
        f"# {name}\n",
        encoding="utf-8",
    )
    return skill_dir


def test_default_product_knowledge_skills_are_discovered(tmp_path, monkeypatch):
    import hermes_cli.main as main_mod

    skills_root = tmp_path / "skills"
    _make_skill(skills_root, "dompet-ku-product-knowledge")
    _make_skill(skills_root, "menu-kita-product-knowledge")
    monkeypatch.setattr("tools.skills_tool.SKILLS_DIR", skills_root, raising=False)

    assert main_mod._default_product_knowledge_skills() == [
        "dompet-ku-product-knowledge",
        "menu-kita-product-knowledge",
    ]


def test_cmd_chat_injects_default_product_knowledge_for_cli(monkeypatch, tmp_path):
    import hermes_cli.main as main_mod

    skills_root = tmp_path / "skills"
    _make_skill(skills_root, "dompet-ku-product-knowledge")
    _make_skill(skills_root, "menu-kita-product-knowledge")
    monkeypatch.setattr("tools.skills_tool.SKILLS_DIR", skills_root, raising=False)
    monkeypatch.setattr(main_mod, "_resolve_use_tui", lambda args: False)
    monkeypatch.setattr(main_mod, "_has_any_provider_configured", lambda: True)
    monkeypatch.setattr(main_mod, "_pin_kanban_board_env", lambda: None)
    monkeypatch.setattr(main_mod, "_prepare_agent_startup", lambda args: None)

    captured = {}
    fake_cli = types.ModuleType("cli")
    fake_cli.main = lambda **kwargs: captured.update(kwargs)
    monkeypatch.setitem(sys.modules, "cli", fake_cli)

    args = SimpleNamespace(
        resume=None,
        continue_last=None,
        query=None,
        image=None,
        model=None,
        provider=None,
        toolsets=None,
        skills=None,
        verbose=False,
        quiet=False,
        worktree=False,
        checkpoints=False,
        pass_session_id=False,
        max_turns=None,
        ignore_rules=False,
        safe_mode=False,
        compact=False,
        accept_hooks=False,
        source=None,
        tui_dev=False,
    )

    main_mod.cmd_chat(args)

    assert captured["skills"] == [
        "dompet-ku-product-knowledge",
        "menu-kita-product-knowledge",
    ]


def test_cmd_chat_injects_default_product_knowledge_for_tui(monkeypatch, tmp_path):
    import hermes_cli.main as main_mod

    skills_root = tmp_path / "skills"
    _make_skill(skills_root, "dompet-ku-product-knowledge")
    monkeypatch.setattr("tools.skills_tool.SKILLS_DIR", skills_root, raising=False)
    monkeypatch.setattr(main_mod, "_resolve_use_tui", lambda args: True)
    monkeypatch.setattr(main_mod, "_has_any_provider_configured", lambda: True)
    monkeypatch.setattr(main_mod, "_pin_kanban_board_env", lambda: None)

    captured = {}

    def fake_launch_tui(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(main_mod, "_launch_tui", fake_launch_tui)

    args = SimpleNamespace(
        resume=None,
        continue_last=None,
        query=None,
        image=None,
        model=None,
        provider=None,
        toolsets=None,
        skills=None,
        verbose=False,
        quiet=False,
        worktree=False,
        checkpoints=False,
        pass_session_id=False,
        max_turns=None,
        ignore_rules=False,
        safe_mode=False,
        compact=False,
        accept_hooks=False,
        source=None,
        tui_dev=False,
    )

    main_mod.cmd_chat(args)

    assert captured["skills"] == ["dompet-ku-product-knowledge"]
