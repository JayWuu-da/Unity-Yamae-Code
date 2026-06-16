# K-Unity-Yamae 한국어 README

**K-Unity-Yamae는 Codex App/CLI 및 Claude Code Desktop/CLI가 Windows 환경에서 Unity 프로젝트를 다룰 때 사용하는 AI 에이전트용 Unity 하네스입니다.**

이 프로젝트는 사람이 직접 쓰는 범용 Unity CLI 제품이 아닙니다. 사용자는 AI 에이전트에게 이 저장소의 git URL을 전달하고, 에이전트가 하네스를 내려받아 설치한 뒤 대상 Unity 프로젝트를 열어 현재 Unity 프로젝트 루트에서 안전 점검, 컨텍스트 수집, 계획, 패치 가드, 검증 계획을 실행하는 구조입니다.

K-Unity-Yamae가 제공하는 정보는 발견된 파일과 발견된 사실에 한정됩니다. 정적 스캔과 context pack은 프로젝트 파일에서 읽은 신호일 뿐이며 Inspector 오브젝트 그래프, prefab override 의도, persistent listener 대상, PlayMode 동작, 빌드 성공을 증명하지 않습니다. 그런 주장은 `editor-probe`, Unity MCP, batchmode, PlayMode, 빌드 로그 같은 실제 증거가 있어야만 가능합니다.

## 에이전트 부트스트랩

AI 에이전트가 git URL만 받은 상태라면 다음 순서로 시작합니다.

```powershell
git clone <K-Unity-Yamae git URL> K-Unity-Yamae
cd K-Unity-Yamae
python -m pip install -e .
python -m pytest -q
python -m ruff check .
python -m kunity_yamae.cli providers doctor --json
```

그 다음 대상 Unity 프로젝트 루트로 이동합니다.

```powershell
cd <현재 Unity 프로젝트 루트>
kunity-yamae init-agent --target both --write --json
kunity-yamae providers doctor --json
```

콘솔 스크립트가 PATH에 없다면 하네스 체크아웃에서 module 형태를 사용합니다.

```powershell
python -m kunity_yamae.cli init-agent --target both --write --json
python -m kunity_yamae.cli providers doctor --json
```

대상 프로젝트에 이미 `AGENTS.md`, `CLAUDE.md`, `.agents/skills/k-unity-yamae/SKILL.md`, `.claude/skills/k-unity-yamae/SKILL.md`, `.claude/commands/kunity-yamae.md`가 있으면 기본 write는 충돌로 멈춰야 합니다. 에이전트는 dry-run 결과를 읽고 기존 파일과 병합해야 하며, 기본값으로 강제 덮어쓰기를 하면 안 됩니다.

## 에이전트 엔트리포인트

K-Unity-Yamae는 실제 AI 도구가 읽을 프로젝트 로컬 안내 파일을 생성합니다.

| 환경 | 엔트리포인트 | 사용 방식 |
| --- | --- | --- |
| Codex App | `AGENTS.md` + `.agents/skills/k-unity-yamae/SKILL.md` | Unity 프로젝트 폴더를 Codex App에서 엽니다. |
| Codex CLI | `AGENTS.md` + `.agents/skills/k-unity-yamae/SKILL.md` | 현재 Unity 프로젝트 루트에서 `codex`를 실행합니다. |
| Claude Code Desktop | `CLAUDE.md` + `.claude/skills/k-unity-yamae/SKILL.md` | Unity 프로젝트 폴더를 Claude Code Desktop에서 엽니다. |
| Claude CLI | `CLAUDE.md` + `.claude/skills/k-unity-yamae/SKILL.md` + `.claude/commands/kunity-yamae.md` | 현재 Unity 프로젝트 루트에서 `claude`를 실행하며 slash command는 primary skill의 호환 래퍼입니다. |

Claude Code Desktop/CLI와 Codex CLI에서는 PowerShell 및 Git for Windows 기준으로 shell/git 동작을 맞추는 편이 안전합니다.

## 에이전트가 호출하는 명령

아래 명령은 사람이 제품처럼 직접 쓰는 설명이 아니라, AI 에이전트가 Unity 작업 전에 호출하는 결정적 하네스 표면입니다.

```powershell
kunity-yamae providers doctor --json
kunity-yamae tools list --json
kunity-yamae context --pretty "Fix prefab button raycast"
kunity-yamae risk --json "Fix prefab button raycast"
kunity-yamae run "Fix prefab button raycast" --plan-only --verify-dry-run --json
kunity-yamae orchestrate "Fix prefab button raycast" --plan-only --verify-dry-run --json
kunity-yamae inspect --json
kunity-yamae inspect --editor-probe --json
kunity-yamae install --codex --claude
```

명시적 프로젝트 경로가 필요한 fixture 테스트에서는 `--project`를 command 앞에 둡니다.

```powershell
kunity-yamae --project <unity-project> init-agent --target both --dry-run --json
kunity-yamae --project <unity-project> run "Fix prefab button raycast" --plan-only --verify-dry-run --json
```

모델이 코드를 수정해야 할 때는 unified diff를 만들게 하고 guarded patch 흐름으로 검증합니다.

```powershell
kunity-yamae run "Fix prefab button raycast" --agent local-patch --patch-file proposed.diff --guarded-agent-patch --json
```

## scan과 context가 읽는 범위

`scan`, `context`, `risk`, `run --plan-only`는 대상 프로젝트에서 발견된 파일과 발견된 사실만 묶습니다.

- `ProjectSettings/ProjectVersion.txt`
- `Packages/manifest.json`
- `.asmdef`
- C# 스크립트와 테스트 어셈블리 후보
- scene, prefab, 일부 serialized text 신호
- 보호 대상/생성물 경로
- UI, graphics, VFX, architecture naming 신호

shared inventory는 발견된 파일, 명령/도구 capability, bounded generic semantic signals를 묶은 저장소 중립 목록입니다. 이는 계획과 위험도 판단에 쓰는 정적 신호이며 Inspector object reference, prefab override 의도, persistent listener target, PlayMode 동작, Game View 상태, build 성공을 증명하지 않습니다.

프로젝트마다 구조, 네이밍, prefab 구성, generated code 위치, 런타임 wiring이 다릅니다. 파일로 발견되지 않은 내용은 unknown으로 남겨야 하며, 에이전트는 모르는 내용을 추측해서 확정적으로 말하면 안 됩니다.

Inspector 오브젝트 그래프, prefab override, persistent listener target, missing serialized reference, UI component state가 필요하면 `kunity-yamae inspect --editor-probe --json` 또는 Unity MCP/batchmode 증거가 필요합니다. Unity Editor, PlayMode, Game View, build, Inspector 검증은 실제로 실행한 증거가 있을 때만 보고합니다.

## Unity MCP와 시각 스모크

Unity MCP는 정적 스캔보다 강한 Editor/Inspector 증거가 필요한 경우에만 사용합니다. 대상 Unity 프로젝트가 MCP 기반 검증을 쓰는 경우 manifest에는 다음 패키지 URL이 들어갈 수 있습니다.

```text
https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main
```

에이전트는 실제 Unity Editor를 실행하지 않은 상태에서는 검증을 완료했다고 말하지 않고, 필요한 live 검증 단계를 dry-run JSON으로 먼저 확인합니다.

```powershell
kunity-yamae verify --dry-run --json --qa-level minimal --live --visual-smoke
```

시각 스모크는 Game View, Console, hierarchy, screenshot 같은 실제 증거가 있을 때만 통과로 보고합니다.

## Unity 안전 규칙

- `.meta`와 GUID 연속성을 보존합니다.
- `.unity`, `.prefab`, `.asset`, `.controller`, `.anim`은 serialized object graph이므로 직접 YAML 편집을 기본값으로 두지 않습니다.
- serialized field rename은 `[FormerlySerializedAs]` 같은 migration 처리가 필요합니다.
- runtime assembly가 `UnityEditor`에 의존하지 않게 합니다.
- Resources/Addressables 문자열 경로 변경은 모든 caller를 추적해야 합니다.
- 쓰기 작업은 한 에이전트만 담당하고, 읽기 전용 분석은 병렬로 수행할 수 있습니다.

## 유지보수 검증

이 저장소 자체를 검증할 때는 다음을 실행합니다.

```powershell
python -m pytest -q
python -m ruff check .
python -m kunity_yamae.cli release-check --json
```

`release-check --json`은 패키지 데이터, Codex/Claude 엔트리포인트, local-patch 준비 상태, AI 에이전트용 문서 계약을 확인합니다. 모델 백엔드 credential 설정 문구나 `.omo`, `plans`, `evidence` 같은 작업 산출물이 프로젝트 산출물처럼 올라가면 안 됩니다.

하네스가 생성한 cache/report는 `.unity-harness/cache/`, `.unity-harness/reports/`, `.unity-harness/last-*` 아래에만 남겨야 합니다. `.omo/`, `.omx/`, `plans/`, `evidence/` 같은 scratch planning/evidence artifacts는 로컬 작업 영수증이며 추적되는 프로젝트 산출물이 아닙니다.

작은 수정은 빠르게, 위험한 변경은 엄격하게, 검증 보고는 실제 증거에 맞게 처리하는 것이 K-Unity-Yamae의 목표입니다.
