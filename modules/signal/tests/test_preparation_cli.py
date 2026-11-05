import contextlib
import io
import re
import sys
import tomllib
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit
from unittest.mock import patch

from typer.testing import CliRunner

from discord_data.cli import app as data_app
from discord_disentanglement.cli import build_parser, main
from discord_filtering.cli import build_parser as build_filtering_parser


class PreparationCliTests(unittest.TestCase):
    def test_pipeline_scope_and_dependencies_exclude_legacy_experiments(self):
        root = Path(__file__).resolve().parents[1]
        for directory in ("approaches", "experiments", "evaluation", "training", "ui"):
            self.assertFalse((root / "discord_disentanglement" / directory).exists())
        self.assertFalse((root / "configs/filtering/games.v1.json").exists())
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(project["name"], "tangletrace-signal")
        self.assertEqual(set(project["scripts"]), {"discord-data", "discord-filter", "discord-prepare"})
        locked = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
        names = {package["name"] for package in locked["package"]}
        local_packages = [
            package["name"]
            for package in locked["package"]
            if package.get("source", {}).get("editable") == "."
        ]
        self.assertEqual(local_packages, [project["name"]])
        self.assertTrue(names.isdisjoint({"scikit-learn", "streamlit", "matplotlib"}))

    def test_primary_cli_help_uses_signal_name(self):
        result = CliRunner().invoke(data_app, ["--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("TangleTrace SIGNAL", result.output)
        self.assertIn("TangleTrace SIGNAL", build_filtering_parser().format_help())
        self.assertIn("TangleTrace SIGNAL", build_parser().format_help())

    def test_pipeline_overview_links_point_to_retained_files(self):
        root = Path(__file__).resolve().parents[1]
        documents = [
            "README.md", "annotations/README.md",
            "docs/methodology/DISENTANGLEMENT_DATASET_PIPELINE.md",
            "docs/methodology/DISCORD_UNVEILED_FILTERING.md",
            *(str(path.relative_to(root)) for path in (root / "reproducibility").glob("*.md")),
        ]
        for relative in documents:
            document = root / relative
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                parsed = urlsplit(target)
                if parsed.scheme or not parsed.path:
                    continue
                with self.subTest(document=relative, target=target):
                    self.assertTrue((document.parent / unquote(parsed.path)).resolve().exists())

    def test_only_data_preparation_commands_are_exposed(self):
        parser = build_parser()
        for command in ("run", "all", "gold-standard", "derive-human-components", "derive-annotation-components"):
            with self.subTest(command=command), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    parser.parse_args([command])
                self.assertEqual(result.exception.code, 2)
        self.assertFalse(any(name.startswith("discord_disentanglement.approaches") for name in sys.modules))

    def test_arguments_reach_the_existing_stage(self):
        with patch("discord_disentanglement.population.main") as handler:
            main(["population", "--memory-limit", "512MB"])
            handler.assert_called_once_with(["--memory-limit", "512MB"])
        with patch("discord_disentanglement.sampling.main") as handler:
            main(["draw", "--seed", "42"])
            handler.assert_called_once_with(["draw", "--seed", "42"])

    def test_stage_help_is_forwarded_without_execution(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as result:
            main(["population", "--help"])
        self.assertEqual(result.exception.code, 0)
        self.assertIn("--memory-limit", output.getvalue())