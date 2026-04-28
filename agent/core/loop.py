from __future__ import annotations

from typing import Optional

from agent.artifacts import ArtifactStore
from agent.core.planner import Planner
from agent.core.prompts import ACTION_SYSTEM_PROMPT
from agent.core.reviewer import Reviewer
from agent.core.state import AgentState
from agent.schemas.actions import AgentDecision
from agent.schemas.outputs import FinalAnswer


class AgentLoop:
    def __init__(
        self,
        planner: Planner,
        executor,
        reviewer: Reviewer,
        provider,
        model: str,
        max_steps: int = 8,
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self.planner = planner
        self.executor = executor
        self.reviewer = reviewer
        self.provider = provider
        self.model = model
        self.max_steps = max_steps
        self.artifact_store = artifact_store

    def _build_transcript(self, state: AgentState) -> str:
        chunks = [f"Task: {state.task}", "", "Notes:"]
        chunks.extend(f"- {note}" for note in state.notes[-20:])
        chunks.append("")
        chunks.append("Action/Observation history:")
        chunks.extend(state.history[-30:])
        return "\n".join(chunks)[-24000:]

    def _log(self, event_type: str, payload) -> None:
        if self.artifact_store is not None:
            self.artifact_store.append_event(event_type, payload)

    def _decide(self, state: AgentState) -> AgentDecision:
        tool_lines = "\n".join(f"- {tool}" for tool in self.executor.available_tools())
        user_prompt = (
            f"Current task:\n{state.task}\n\n"
            f"Available tools:\n{tool_lines}\n\n"
            f"Current state:\n{self._build_transcript(state)}\n\n"
            "Return the single best next decision."
        )
        if self.artifact_store is not None:
            self.artifact_store.write_json(
                f"prompts/step_{state.step_count:02d}_decision_prompt.json",
                {
                    "system_prompt": ACTION_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_prompt}],
                    "model": self.model,
                    "tools": self.executor.tool_schemas(),
                },
            )
        decision = self.provider.decide_action(
            system_prompt=ACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            model=self.model,
            tools=self.executor.tool_schemas(),
            decision_schema=AgentDecision,
        )
        self._log("decision", {"step": state.step_count, "decision": decision})
        return decision

    def _finalize_from_decision(self, decision: AgentDecision, state: AgentState) -> FinalAnswer:
        summary = decision.summary or "Agent stopped without a final summary."
        next_steps = decision.next_steps or []
        changed_files = sorted(set([*state.changed_files, *decision.changed_files]))
        commands_run = state.commands_run
        return FinalAnswer(
            summary=summary,
            changed_files=changed_files,
            commands_run=commands_run,
            next_steps=next_steps,
        )

    def run(self, task: str):
        state = AgentState(task=task)
        if self.artifact_store is not None:
            state.artifact_dir = str(self.artifact_store.root)
            state.run_id = self.artifact_store.run_id
            self.artifact_store.write_text("task.txt", task + "\n")
            self._log("run_started", {"task": task, "model": self.model})
            self.artifact_store.write_json(
                "prompts/plan_prompt.json",
                {
                    "system_prompt": "Create a concise implementation plan for the task.",
                    "messages": [{"role": "user", "content": task}],
                    "model": self.model,
                },
            )

        try:
            project_summary = self.executor.validation.detect_project()
            state.notes.append("Project profile:\n" + project_summary)
            self._log("project_detected", {"summary": project_summary})
        except Exception as exc:  # noqa: BLE001
            state.notes.append(f"Project profile unavailable: {type(exc).__name__}: {exc}")

        plan = self.planner.create_plan(task)
        if self.artifact_store is not None:
            self.artifact_store.write_json("outputs/plan.json", plan)
            self._log("plan_created", plan)
        state.notes.append(f"Plan: {plan.summary}")
        for step in plan.steps:
            state.notes.append(f"Step {step.id}: {step.title} - {step.description}")

        final_answer: Optional[FinalAnswer] = None

        for step_number in range(1, self.max_steps + 1):
            state.step_count = step_number
            decision = self._decide(state)
            reasoning = decision.reasoning or ""
            if decision.decision == "final":
                state.finished = True
                state.history.append(f"STEP {step_number} FINAL: {reasoning}")
                final_answer = self._finalize_from_decision(decision, state)
                self._log("final_from_decision", final_answer)
                break

            if decision.tool is None:
                state.finished = True
                final_answer = FinalAnswer(
                    summary="Agent stopped because the model returned a tool decision without a tool.",
                    changed_files=sorted(set(state.changed_files)),
                    commands_run=state.commands_run,
                    next_steps=["Retry with a model that supports tool calling or JSON outputs more reliably."],
                )
                self._log("final_error", final_answer)
                break

            tool_action = decision.tool
            state.actions_taken.append(tool_action.tool)
            state.history.append(
                f"STEP {step_number} ACTION {tool_action.tool}: {tool_action.args}"
                + (f" | reasoning={tool_action.reasoning}" if tool_action.reasoning else "")
            )
            self._log("tool_selected", {"step": step_number, "tool": tool_action})
            try:
                result, changed_files, commands_run = self.executor.run_tool(
                    tool_action.tool,
                    tool_action.args,
                )
                state.changed_files.extend(changed_files)
                state.commands_run.extend(commands_run)
                state.history.append(f"STEP {step_number} OBSERVATION:\n{result[-12000:]}")
                if self.artifact_store is not None:
                    self.artifact_store.write_json(
                        f"outputs/step_{step_number:02d}_tool.json",
                        {
                            "tool": tool_action.tool,
                            "args": tool_action.args,
                            "changed_files": changed_files,
                            "commands_run": commands_run,
                        },
                    )
                    self.artifact_store.write_text(
                        f"outputs/step_{step_number:02d}_result.txt",
                        result,
                    )
                self._log(
                    "tool_result",
                    {
                        "step": step_number,
                        "tool": tool_action.tool,
                        "changed_files": changed_files,
                        "commands_run": commands_run,
                        "result_preview": result[-2000:],
                    },
                )
            except Exception as exc:  # noqa: BLE001
                state.history.append(f"STEP {step_number} ERROR: {type(exc).__name__}: {exc}")
                self._log("tool_error", {"step": step_number, "tool": tool_action.tool, "error": f"{type(exc).__name__}: {exc}"})

        if final_answer is None:
            state.finished = True
            transcript = self._build_transcript(state)
            if self.artifact_store is not None:
                self.artifact_store.write_json(
                    "prompts/reviewer_prompt.json",
                    {
                        "system_prompt": "Summarize the result of the execution run clearly and concisely.",
                        "messages": [{"role": "user", "content": f"Task: {task}\n\nTranscript:\n{transcript}"}],
                        "model": self.model,
                    },
                )
            final_answer = self.reviewer.summarize(task, transcript)
            final_answer.changed_files = sorted(set([*final_answer.changed_files, *state.changed_files]))
            final_answer.commands_run = state.commands_run
            self._log("final_from_reviewer", final_answer)

        if self.artifact_store is not None:
            self.artifact_store.write_json("outputs/final_summary.json", final_answer)
            self.artifact_store.write_json(
                "outputs/run_state.json",
                {
                    "task": state.task,
                    "step_count": state.step_count,
                    "actions_taken": state.actions_taken,
                    "commands_run": state.commands_run,
                    "changed_files": sorted(set(state.changed_files)),
                    "finished": state.finished,
                },
            )
            self._log("run_finished", {"step_count": state.step_count, "finished": state.finished})

        return plan, state, final_answer
