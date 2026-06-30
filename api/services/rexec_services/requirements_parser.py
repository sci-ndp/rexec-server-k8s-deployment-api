"""
Parsing and loading of Python requirements for the Rexec server image.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import Specifier

from .exceptions import RexecConfigurationError, RexecValidationError


def parse_requirements(requirements: Iterable[str]) -> tuple[str, List[str]]:
    """
    Separate the python version requirement from the rest of the packages.
    Returns a tuple of (python_version, user_requirements_list).
    """
    python_version: str | None = None
    user_requirements: List[str] = []

    for raw_requirement in requirements:
        requirement_str = raw_requirement.strip()
        if not requirement_str:
            continue
        try:
            parsed = Requirement(requirement_str)
        except InvalidRequirement as exc:
            raise RexecValidationError(
                f"Invalid requirement '{requirement_str}': {exc}"
            ) from exc

        if parsed.name.lower() == "python":
            try:
                specifier: Specifier = next(iter(parsed.specifier))
            except StopIteration as exc:
                raise RexecValidationError(
                    "Python requirement must pin the version using '=='."
                ) from exc

            if specifier.operator != "==":
                raise RexecValidationError(
                    "Python requirement must use '==' to pin a single version."
                )
            python_version = specifier.version
        else:
            user_requirements.append(requirement_str)

    if not python_version:
        raise RexecValidationError(
            "A pinned Python version (e.g., 'python==3.11') is required."
        )

    return python_version, user_requirements


def load_builtin_requirements() -> List[str]:
    """Read the packaged requirements for the base Rexec server image."""
    requirements_file = Path(__file__).parent / "SciDx_rexec_server" / "requirements.txt"
    if not requirements_file.exists():
        raise RexecConfigurationError(
            f"Builtin requirements file missing: {requirements_file}"
        )

    requirements: List[str] = []
    with requirements_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            requirement = line.strip()
            if requirement and not requirement.startswith("#"):
                requirements.append(requirement)

    return requirements
