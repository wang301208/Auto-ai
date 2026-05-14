"""Async interaction loop for the merged architecture.

Provides both sync and async entry points for the agent interaction
loop, using AsyncAgent for non-blocking operation.

Supports optional multi-agent coordination via AgentCommunicationBus
and multi-agent TUI observation window.
"""

from __future__ import annotations

import asyncio
import math
import signal
import time
from enum import Enum
from typing import Any, Optional

from autoai.app.i18n import _
from autoai.config import Config
from autoai.logs import logger
from autoai.models.command_registry import CommandRegistry


class UserFeedback(Enum):
    AUTHORIZE = "authorize"
    EXIT = "exit"
    TEXT = "text"


async def run_async_interaction_loop(
    agent: Any,
    config: Config,
    cycle_budget: int = 1,
    comm_bus: Any | None = None,
    multi_tui: Any | None = None,
) -> None:
    """Async version of the agent interaction loop.

    Replaces the sync while-loop in autoai/app/main.py with an
    async equivalent using AsyncAgent.async_think() and
    AsyncAgent.async_execute_step().

    When comm_bus is provided, the agent can receive tasks from
    other agents and send results back.

    When multi_tui is provided, the observation window is updated
    each cycle with agent status.

    Args:
        agent: An AsyncAgent instance.
        config: Application configuration.
        cycle_budget: Number of cycles to run (1 = require approval each step).
        comm_bus: Optional AgentCommunicationBus for multi-agent coordination.
        multi_tui: Optional MultiAgentTUI for observation.
    """
    from autoai.agents.async_agent import AsyncAgent

    if not isinstance(agent, AsyncAgent):
        raise TypeError(f"Expected AsyncAgent, got {type(agent).__name__}")

    cycles_remaining = cycle_budget
    cycle_count = 0
    start_time = time.time()

    def _handle_sigint(sig: int, frame: Any) -> None:
        nonlocal cycles_remaining
        if cycles_remaining == math.inf:
            logger.info(
                _("Interrupt signal received. Stopping continuous command execution.")
            )
            cycles_remaining = 1
        else:
            logger.info(
                _(
                    "Interrupt signal received. Stopping continuous command execution immediately."
                )
            )
            cycles_remaining = 0

    signal.signal(signal.SIGINT, _handle_sigint)

    while cycles_remaining > 0:
        cycle_count += 1

        if comm_bus is not None:
            msg = comm_bus.receive(agent.ai_config.ai_name)
            if msg is not None:
                logger.info(
                    f"[comm] Received {msg.message_type.value} from {msg.sender_id}: "
                    f"{str(msg.payload)[:80]}"
                )

        try:
            command_name, command_args, assistant_reply_dict = await agent.async_think()
        except Exception as e:
            logger.error(f"Error during think: {e}")
            break

        if command_name is None:
            logger.info(_("The Agent failed to select an action."))
            cycles_remaining = 1
            continue

        logger.info(
            f"Next Action: {command_name}"
            + (f"({command_args})" if command_args else "")
        )

        if cycles_remaining == 1:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input(_("Waiting for your response...") + "\n")
            )
            if user_input.lower() in {"n", "exit", "quit"}:
                logger.info(_("Exiting..."))
                break

        if command_name != "human_feedback":
            cycles_remaining -= 1

        try:
            result = await agent.async_execute_step(
                command_name, command_args, user_input=None
            )
        except Exception as e:
            from autoai.agents.async_agent import CommandRepetitionError

            if isinstance(e, CommandRepetitionError):
                result = str(e)
                cycles_remaining = 1
            else:
                logger.error(f"Error during execute: {e}")
                break

        if result is not None:
            logger.info(f"SYSTEM: {result}")

        if multi_tui is not None:
            try:
                from autoai.app.multi_agent_tui import AgentViewData
                uptime = time.time() - start_time
                multi_tui.update_agent(AgentViewData(
                    agent_id=agent.ai_config.ai_name,
                    name=agent.ai_config.ai_name,
                    role="primary",
                    autonomous=getattr(agent, "autonomous_mode", False),
                    cycle_count=cycle_count,
                    tasks_done=cycle_count,
                    current_task=str(command_name) if command_name else "",
                    status="running",
                ))
                if cycle_count % 10 == 0:
                    multi_tui.render_once()
            except Exception:
                pass

        if hasattr(agent, "_policy_evolver") and cycle_count % 100 == 0:
            try:
                evolver = agent._policy_evolver
                result = evolver.evolve(lookback_hours=1.0)
                if result.adjustments:
                    logger.info(f"[evolver] {len(result.adjustments)} policy adjustments applied")
            except Exception:
                pass

        if hasattr(agent, "_self_think_engine") and cycle_count % 50 == 0 and cycle_count > 0:
            try:
                engine = agent._self_think_engine
                if engine.auto_fix:
                    summary = await engine.auto_fix_cycle(
                        getattr(agent, "_task_queue", []),
                        fix_executor=getattr(agent, "_fix_executor", None),
                    )
                    if summary["discovered"] > 0:
                        logger.info(
                            f"[self-evolve] discovered={summary['discovered']} "
                            f"fixed={summary['fixed']} verified={summary['verified']} "
                            f"failed={summary['failed']}"
                        )
            except Exception:
                pass

    logger.info(_("Task completed."))


def run_sync_interaction_loop(
    agent: Any,
    config: Config,
    cycle_budget: int = 1,
    comm_bus: Any | None = None,
    multi_tui: Any | None = None,
) -> None:
    """Synchronous wrapper for the async interaction loop.

    Provides backward compatibility for existing code that expects
    a sync entry point.
    """
    asyncio.run(run_async_interaction_loop(
        agent, config, cycle_budget,
        comm_bus=comm_bus,
        multi_tui=multi_tui,
    ))
