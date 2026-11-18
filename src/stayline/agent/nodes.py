"""Async nodes for the guarded agent graph."""

import json
from datetime import date
from time import perf_counter
from typing import Callable

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt

from stayline.agent.harness import render_observation
from stayline.agent.prompts import CONTROL_SPECS, SYSTEM_PROMPT
from stayline.agent.router import give_up_reason
from stayline.agent.state import AgentState
from stayline.memory.aliases import recall_aliases, remember_alias
from stayline.servers.results import ToolResult


def _recall_message(store, state: AgentState) -> dict | None:
    """Offer the operator's stored aliases as lookup hints, never as evidence."""
    if store is None:
        return None
    aliases = recall_aliases(store, state["operator_id"])
    if not aliases:
        return None
    hints = {alias: {key: value[key] for key in ("case_reference", "court")}
             for alias, value in aliases.items()}
    return {"role": "system", "content": (
        "Known aliases for this operator (lookup hints only, verify against current "
        f"records): {json.dumps(hints, ensure_ascii=False)}"
    )}


def _message(call_id: str, content: str) -> dict:
    """Make one OpenAI tool response message."""
    return {"role": "tool", "tool_call_id": call_id, "content": content}


def _entry(tool: str, args: dict, result: ToolResult, ms: int) -> dict:
    """Record a tool call without untrusted data or secrets."""
    return {
        "tool": tool, "args": args, "ok": result.ok,
        "error_code": result.error.code if result.error else None, "ms": ms,
    }


def _run_id(config: dict) -> str:
    """Read the checkpoint thread id used for keyed calls."""
    return config["configurable"]["thread_id"]


def _decision(value) -> dict:
    """Accept the same decision forms as the course Studio."""
    if isinstance(value, dict):
        return value
    text = str(value).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        text = str(parsed)
    except ValueError:
        pass
    return {
        "approve": text.lower() in {"true", "yes", "y", "ok", "approve"},
        "reason": text,
    }


def make_nodes(harness, llm, store=None) -> dict[str, Callable]:
    """Bind graph nodes to a tool harness and model."""

    async def call(tool: str, args: dict, config: RunnableConfig) -> tuple[ToolResult, dict]:
        started = perf_counter()
        result = await harness.call(tool, args, _run_id(config))
        ms = round((perf_counter() - started) * 1000)
        return result, _entry(tool, args, result, ms)

    async def recall(state: AgentState) -> dict:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": state["task"]},
        ]
        memory = _recall_message(store, state)
        if memory is not None:
            messages.append(memory)
        return {"messages": messages}

    async def think(state: AgentState) -> dict:
        reply = await llm.complete(state["messages"], harness.tool_specs() + CONTROL_SPECS)
        assistant = dict(reply.message)
        calls = assistant.get("tool_calls") or []
        if calls:
            assistant["tool_calls"] = calls[:1]
        update = {
            "messages": [assistant], "model_calls": state["model_calls"] + 1,
            "usage": [reply.usage],
        }
        if not calls:
            update.update(action={"type": "none"}, answer=assistant.get("content") or "")
            return update
        first = calls[0]
        name = first["function"]["name"]
        call_id = first["id"]
        try:
            args = json.loads(first["function"].get("arguments") or "{}")
            if not isinstance(args, dict):
                raise ValueError("Tool arguments must be an object")
        except (ValueError, TypeError):
            update["action"] = {"type": "none"}
            update["messages"].append(_message(call_id, "The arguments were not valid JSON."))
            return update
        finals = {"finish": ("done", "summary"),
                  "ask_operator": ("asked_operator", "question"),
                  "refuse": ("refused", "reason")}
        if name in finals:
            stop, key = finals[name]
            answer = args.get(key, "")
            update.update(
                action={"type": "final", "stop": stop, "text": answer},
                stop_reason=stop, answer=answer,
            )
            update["messages"].append(_message(call_id, "ok"))
            return update
        update["action"] = {
            "type": "call", "tool": name, "args": args, "call_id": call_id,
        }
        return update

    async def remind(state: AgentState) -> dict:
        return {
            "reminded": True,
            "messages": [{"role": "user", "content":
                          "End the run by calling finish, ask_operator or refuse."}],
        }

    async def remember(state: AgentState) -> dict:
        args = state["action"]["args"]
        if store is None:
            content = {"ok": False, "error": {
                "code": "internal", "message": "Memory is not available.",
            }}
        else:
            fields = ("alias", "case_reference", "court")
            stored = all(isinstance(args.get(key), str) for key in fields) and remember_alias(
                store, state["operator_id"], *(args[key] for key in fields),
                operator_message=state["task"],
            )
            content = {"ok": True, "data": {"stored": True}} if stored else {
                "ok": False, "error": {
                    "code": "invalid_argument",
                    "message": "Not stored: the alias, case reference and court must all "
                               "appear in the operator's own message.",
                },
            }
        return {"messages": [_message(state["action"]["call_id"], json.dumps(content))]}

    async def read_tool(state: AgentState, config: RunnableConfig) -> dict:
        action = state["action"]
        result, entry = await call(action["tool"], action["args"], config)
        return {
            "messages": [_message(action["call_id"], render_observation(result))],
            "tool_calls": [entry],
        }

    async def prepare(state: AgentState, config: RunnableConfig) -> Command:
        action = state["action"]
        tool, args = action["tool"], action["args"]
        log: list[dict] = []

        async def fetch(name: str, arguments: dict):
            result, entry = await call(name, arguments, config)
            log.append(entry)
            if not result.ok:
                return result, None
            return None, result.data

        async def failed(result: ToolResult) -> Command:
            return Command(goto="think", update={
                "tool_calls": log,
                "messages": [_message(action["call_id"], render_observation(result))],
            })

        if tool == "apply_seizure":
            error, source = await fetch("get_notice", {"notice_id": args.get("notice_id")})
        else:
            error, source = await fetch("get_operation_request", {"request_id": args.get("request_id")})
        if error:
            return await failed(error)
        contract_id = args.get("contract_id")
        error, contract = await fetch("get_contract", {"contract_id": contract_id})
        if error:
            return await failed(error)
        preview = {
            "tool": tool,
            "args": {"notice_id" if tool == "apply_seizure" else "request_id":
                     args.get("notice_id" if tool == "apply_seizure" else "request_id"),
                     "contract_id": contract_id, "expected_version": contract["version"]},
            "contract": {key: contract[key] for key in
                         ("contract_id", "policy_number", "status", "version")},
        }
        if tool == "apply_seizure":
            target = source["target"]
            error, match = await fetch("find_contracts", {
                "subscriber_identity": {key: target[key] for key in
                                        ("last_name", "first_names", "birth_date", "birth_place_code")},
                "contract_reference": target["policy_number"],
            })
            if error:
                return await failed(error)
            error, rule = await fetch("get_rule", {
                "rule_id": "CPP-706-155", "as_of_date": date.today().isoformat(),
            })
            if error:
                return await failed(error)
            candidate = next((item for item in match["candidates"]
                              if item["contract_id"] == contract_id), None)
            preview["source"] = {key: source[key] for key in (
                "notice_id", "court_id", "judge_role", "procedure_type", "case_reference"
            )}
            preview["match"] = {
                "outcome": match["outcome"],
                "evidence": candidate["evidence"] if candidate else [],
            }
            preview["effect"] = {
                "restrictions": rule["restrictions"],
                "rule": f'{rule["rule_id"]}@{rule["version"]}',
            }
        else:
            error, ledger = await fetch("get_restriction_ledger", {"contract_id": contract_id})
            if error:
                return await failed(error)
            preview["source"] = {key: source[key] for key in (
                "request_id", "type", "origin", "amount_eur", "target_allocation"
            )}
            effect = {"type": source["type"]}
            field = "target_allocation" if source["type"] == "arbitrage" else "amount_eur"
            effect[field] = source[field]
            preview["effect"] = effect
            preview["active_restrictions"] = [row["restriction"] for row in ledger]
        return Command(goto="approve", update={"preview": preview, "tool_calls": log})

    async def approve(state: AgentState) -> Command:
        decision = interrupt(state["preview"])
        decision = _decision(decision)
        update = {"approvals": [{"preview": state["preview"], "decision": decision}]}
        if decision.get("approve"):
            return Command(goto="write", update=update)
        reason = decision.get("reason", "")
        update["messages"] = [_message(
            state["action"]["call_id"], f"rejected by the human: {reason}"
        )]
        return Command(goto="think", update=update)

    async def write(state: AgentState, config: RunnableConfig) -> Command:
        preview = state["preview"]
        result, entry = await call(preview["tool"], preview["args"], config)
        log = [entry]
        if result.error and result.error.code == "stale_version":
            next_node = "give_up" if len(state["tool_calls"]) + 1 >= state["max_steps"] else "prepare"
            return Command(goto=next_node, update={"tool_calls": log})
        return Command(goto="verify", update={
            "tool_calls": log, "last_write": result.model_dump(),
        })

    async def verify(state: AgentState, config: RunnableConfig) -> dict:
        preview = state["preview"]
        write_result = ToolResult.model_validate(state["last_write"])
        logs: list[dict] = []

        async def read_back() -> tuple[ToolResult, bool]:
            tool = "get_restriction_ledger" if preview["tool"] == "apply_seizure" else "get_operation_request"
            args = ({"contract_id": preview["args"]["contract_id"]}
                    if tool == "get_restriction_ledger" else
                    {"request_id": preview["args"]["request_id"]})
            result, entry = await call(tool, args, config)
            logs.append(entry)
            if not result.ok:
                return result, False
            if tool == "get_operation_request":
                return result, result.data["status"] == "executed"
            notice_id = preview["args"]["notice_id"]
            confirmed = all(any(
                row["restriction"] == restriction and row["notice_id"] == notice_id
                for row in result.data
            ) for restriction in preview["effect"]["restrictions"])
            return result, confirmed

        read_result, confirmed = await read_back()
        if write_result.error and write_result.error.outcome_unknown and not confirmed:
            write_result, entry = await call(preview["tool"], preview["args"], config)
            logs.append(entry)
            read_result, confirmed = await read_back()
        if confirmed and (write_result.ok or
                          (write_result.error and write_result.error.outcome_unknown)):
            content = {
                "ok": True,
                "data": write_result.data if write_result.ok else read_result.data,
                "confirmed_by_read_back": True,
            }
            if write_result.error and write_result.error.outcome_unknown:
                content["note"] = "The write timed out but the read-back shows it was applied."
            observation = json.dumps(content, ensure_ascii=False)
        elif not write_result.ok:
            observation = render_observation(write_result)
        else:
            observation = json.dumps({"ok": False, "error": {
                "code": "internal",
                "message": "The write reported success but the read-back did not confirm it.",
            }})
        return {
            "tool_calls": logs,
            "messages": [_message(state["action"]["call_id"], observation)],
        }

    async def give_up(state: AgentState) -> dict:
        return {"stop_reason": give_up_reason(state), "answer": None}

    return {name: value for name, value in locals().items() if name in {
        "recall", "think", "remind", "remember", "read_tool", "prepare",
        "approve", "write", "verify", "give_up",
    }}
