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

  if [[ ! "$skill_name" =~ ^pm-[a-z0-9]+(-[a-z0-9]+)+$ ]]; then
    fail "$skill_name must use lowercase pm-object-action kebab-case"
  fi

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

  if ! grep -Fqx "# $skill_name" "$skill_file"; then
    fail "$skill_file top-level title must be '# $skill_name'"
  fi

  if ! grep -Eq '^## 默认输出(结构)?$' "$skill_file"; then
    fail "$skill_file missing required heading '## 默认输出' or '## 默认输出结构'"
  fi

  for required_heading in "## 优先读取" "## 完成标准"; do
    if ! grep -Fqx "$required_heading" "$skill_file"; then
      fail "$skill_file missing required heading '$required_heading'"
    fi
  done

  agent_file="$skill_dir/agents/openai.yaml"
  if [ ! -f "$agent_file" ]; then
    fail "$agent_file is required"
  fi

  if ! grep -Eq '^interface:' "$agent_file"; then
    fail "$agent_file missing interface section"
  fi

  if ! grep -Eq '^policy:' "$agent_file"; then
    fail "$agent_file missing policy section"
  fi

  if ! grep -Eq '^[[:space:]]*short_description:' "$agent_file"; then
    fail "$agent_file missing interface short_description"
  fi

  if ! grep -Eq '^[[:space:]]*default_prompt:' "$agent_file"; then
    fail "$agent_file missing interface default_prompt"
  fi

  display_name="$(
    sed -n 's/^[[:space:]]*display_name:[[:space:]]*//p' "$agent_file" \
      | head -n 1 \
      | sed "s/^['\"]//; s/['\"]$//"
  )"

  if [ "$display_name" != "$skill_name" ]; then
    fail "$agent_file display_name '$display_name' does not match '$skill_name'"
  fi

  if ! grep -Fq "\$$skill_name" "$agent_file"; then
    fail "$agent_file default_prompt must mention \$$skill_name"
  fi
done < <(find skills -mindepth 1 -maxdepth 1 -type d | sort)

if [ "$skill_count" -eq 0 ]; then
  fail "no skill directories found under skills/"
fi

if [ -d "commands" ]; then
  while IFS= read -r command_file; do
    command_name="$(basename "$command_file" .md)"
    if ! grep -Fqx "# $command_name" "$command_file"; then
      fail "$command_file top-level title must be '# $command_name'"
    fi
  done < <(find commands -mindepth 1 -maxdepth 1 -type f -name '*.md' | sort)
fi

echo "Validated $skill_count skills successfully."
