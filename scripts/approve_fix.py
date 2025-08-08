"""CLI to publish an ApprovalGranted event once a fix is reviewed."""

from __future__ import annotations

import argparse

from autogpt.event_bus import ApprovalGranted, EventBus, MessageQueue


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish an ApprovalGranted event for a reviewed fix"
    )
    parser.add_argument(
        "--branch",
        required=True,
        help="Branch containing the approved fix",
    )
    parser.add_argument(
        "--commit",
        required=True,
        dest="commit_hash",
        help="Commit hash of the approved fix",
    )
    parser.add_argument(
        "--summary",
        required=True,
        help="Short description of the approved fix",
    )
    parser.add_argument(
        "--approved-by",
        required=True,
        help="Identifier for the human approver",
    )
    parser.add_argument(
        "--db-path",
        default="events.db",
        help="Path to the event database",
    )
    args = parser.parse_args()

    bus = EventBus(args.db_path)
    mq = MessageQueue(bus)
    event = ApprovalGranted(
        branch_name=args.branch,
        commit_hash=args.commit_hash,
        summary=args.summary,
        approved_by=args.approved_by,
    )
    mq.publish(event)
    print("ApprovalGranted event published for branch", args.branch)


if __name__ == "__main__":
    main()
