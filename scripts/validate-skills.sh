#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

skill_count=0

if [ ! -d "skills" ]; then
  fail "missing skills/ directory"
fi

while IFS= read -r skill_dir; do
  skill_count=$((skill_count + 1))
  skill_name="$(basename "$skill_dir")"
  skill_file="$skill_dir/SKILL.md"

  if [ ! -f "$skill_file" ]; then
    fail "missing $skill_file"
  fi

  declared_name="$(
    sed -n 's/^name:[[:space:]]*//p' "$skill_file" \
      | head -n 1 \
      | sed "s/^['\"]//; s/['\"]$//"
  )"

  if [ -z "$declared_name" ]; then
    fail "$skill_file missing front matter name"
  fi

  if [ "$declared_name" != "$skill_name" ]; then
    fail "$skill_file name '$declared_name' does not match directory '$skill_name'"
  fi

  if ! grep -Eq '^description:[[:space:]]*.+$' "$skill_file"; then
    fail "$skill_file missing description front matter"
  fi

  if ! grep -Eq '^# ' "$skill_file"; then
    fail "$skill_file missing top-level title"
  fi

  if [ -d "$skill_dir/agents" ]; then
    if [ ! -f "$skill_dir/agents/openai.yaml" ]; then
      fail "$skill_dir/agents exists but openai.yaml is missing"
    fi

    if ! grep -Eq '^interface:' "$skill_dir/agents/openai.yaml"; then
      fail "$skill_dir/agents/openai.yaml missing interface section"
    fi

    if ! grep -Eq '^policy:' "$skill_dir/agents/openai.yaml"; then
      fail "$skill_dir/agents/openai.yaml missing policy section"
    fi
  fi
done < <(find skills -mindepth 1 -maxdepth 1 -type d | sort)

if [ "$skill_count" -eq 0 ]; then
  fail "no skill directories found under skills/"
fi

if [ -d "commands" ]; then
  while IFS= read -r command_file; do
    if ! grep -Eq '^# ' "$command_file"; then
      fail "$command_file missing top-level title"
    fi
  done < <(find commands -mindepth 1 -maxdepth 1 -type f -name '*.md' | sort)
fi

echo "Validated $skill_count skills successfully."
