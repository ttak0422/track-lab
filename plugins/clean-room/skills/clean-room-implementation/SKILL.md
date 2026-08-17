---
name: clean-room-implementation
description: Coordinate clean-room or black-box compatibility implementation through separated specification, implementation, and conformance agents. Use when building an emulator, compatible replacement, protocol implementation, file-format reader, API clone, or other interoperability work where the implementer must receive only an approved behavioral specification.
compatibility: Codex and OpenCode; OpenCode agents use opencode-go/gpt-5.6-luna.
---

# Clean-room implementation

Separate observation from implementation. The deliverable is not just compatible code: it is a traceable
handoff showing what the implementer received and how the verifier checked it.

This workflow is process guidance, not legal advice. Before observing a target, establish that the work
is authorized and identify relevant license, contract, anti-circumvention, patent, trademark, privacy,
and jurisdiction-specific constraints. Stop when authorization or the permitted observation methods are
unclear.

Read [`references/artifact-contract.md`](references/artifact-contract.md) before starting.

## Invariants

- Use separate observation and implementation directories that are not nested inside each other.
- Keep the observable target inside the observation directory; phase agents cannot access external
  directories.
- Never give the implementer target source, decompiler output, raw observation logs, or conversation
  history from the specification phase.
- Move only the reviewed `.clean-room/approved/` package across the boundary.
- Start the implementer and verifier in fresh sessions. Never continue or fork the specifier session.
- Treat model separation as process discipline, not a security boundary. Use OS-level isolation when the
  boundary must be enforceable.
- Keep observed behavior, public documentation, and inference distinguishable.
- Do not claim legal cleanliness or conformance merely because the workflow completed.

## OpenCode model profile

OpenCode Go currently exposes GPT through `opencode-go/gpt-5.6-luna`. Use model variants to allocate
effort:

| Role | Agent | Variant |
| ---- | ----- | ------- |
| Coordinator | `clean-room-orchestrator` | `high` |
| Specification | `clean-room-specifier` | `max` |
| Implementation | `clean-room-implementer` | `medium` |
| Verification | `clean-room-verifier` | `max` |

Do not silently substitute another provider or model. If the configured model is unavailable, report the
blocker and let the user select a replacement.

## 1. Establish the boundary

Write `.clean-room/boundary.md` and record:

- the target and compatibility goal;
- permitted observation methods and prohibited materials;
- the observation directory and independent implementation directory;
- the public interfaces in scope;
- acceptance criteria and non-goals;
- who approves the specification package.

The implementation directory must not contain or reference the observation directory. Check both trees
before implementation begins. If this cannot be established, stop rather than calling the process
clean-room.

## 2. Specify in the observation environment

Run `clean-room-specifier` in a fresh session rooted at the observation directory. It may inspect only
materials allowed by the recorded boundary. It writes raw material to `.clean-room/evidence/` and the
candidate handoff to `.clean-room/candidate/`.

Require:

- stable requirement identifiers;
- reproducible experiments and exact results;
- positive, negative, boundary, and state-transition behavior;
- explicit uncertainty instead of guessed behavior;
- original behavioral descriptions rather than copied implementation expression;
- provenance linking each requirement to evidence.

Have the designated human approver review the candidate outside the agent loop before crossing the
boundary. The approver removes unnecessary expressive material and anything whose use was not approved,
then creates `.clean-room/approved/` with the accepted files and the required `APPROVAL.md`. Neither the
specifier nor the orchestrator can approve the draft. Verify the recorded digests before copying the
package to the implementation environment.

## 3. Implement in an isolated fresh session

Copy only `.clean-room/approved/` into the implementation directory. Start
`clean-room-implementer` there with a new context. Its task prompt may contain the compatibility goal,
approved-package path, implementation constraints, and completion criteria. It must not contain a
summary of observation-only material.

The implementer:

- maps code and tests to requirement identifiers;
- implements only specified behavior;
- records ambiguities as questions against requirement identifiers;
- does not search for the target source or undocumented internals;
- does not invent behavior to make tests pass;
- runs the implementation project's ordinary tests and reports exact outcomes.

Questions cross back as requirement-level questions. The specifier may update the candidate package,
but the answer must not include raw evidence or internal implementation detail. The designated approver
must review and approve a new package revision. Start a new implementation session after a material
specification update.

## 4. Verify from a fresh context

Start `clean-room-verifier` in a new session rooted at the implementation directory. Give it the approved
package and independent implementation, but no observation session or raw evidence.

The verifier:

- checks every normative requirement;
- runs approved conformance tests and relevant project tests;
- cites command results from its own session;
- distinguishes failures from checks that could not be performed;
- writes `.clean-room/reports/conformance.md` using the artifact contract;
- does not edit implementation code.

For failures, return only the requirement identifier, expected behavior, observed implementation
behavior, and reproduction command to the implementer. Repeat implementation and fresh verification
until conformant or explicitly stopped. Never weaken the specification solely to accept the current
implementation.

## 5. Finish with an audit summary

Write `.clean-room/reports/audit.md` and report:

- approved-package revision or digest;
- implementation revision;
- conformance result;
- unresolved requirements and legal/process caveats;
- where observation-only evidence and implementation artifacts reside;
- confirmation that only the approved package crossed the boundary, or an explicit disclosure that the
  invariant was not verified.

State that a `conformant` result covers the approved specification only and does not independently prove
that the specification is complete relative to the target.
