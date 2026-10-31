#!/usr/bin/env python3
"""Ask Muse Spark questions about an ingested video's temporal memory.

Credentials come from backend/.env or the process environment.
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv

from backend.memory.repository import Neo4jMemoryRepository
from backend.reasoning.models import ReasoningError
from backend.reasoning.muse_client import DEFAULT_MODEL, MuseClient
from backend.reasoning.reasoning_service import ReasoningService


def print_answer(answer, verbose):
    print(f"\n{answer.answer}")
    if not answer.sufficient_evidence:
        print("(insufficient evidence)")
    if answer.evidence:
        print("\nEvidence:")
        for item in answer.evidence:
            print(f"  [{item.evidence_id}] {item.text}")
            if item.evidence_uri:
                print(f"       source: {item.evidence_uri}")
    if verbose:
        print("\nInterpreted intent:", answer.intent.model_dump_json())


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="omit to start an interactive prompt")
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--model", default=os.environ.get("MUSE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--json", action="store_true", help="print the full answer as JSON")
    parser.add_argument("--verbose", action="store_true", help="show the interpreted intent")
    args = parser.parse_args()
    required = ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "META_API_KEY")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        parser.error("Missing environment variables: " + ", ".join(missing))

    muse = MuseClient(os.environ["META_API_KEY"], model=args.model)
    with Neo4jMemoryRepository.connect(os.environ["NEO4J_URI"], os.environ["NEO4J_USERNAME"],
                                       os.environ["NEO4J_PASSWORD"],
                                       os.environ.get("NEO4J_DATABASE")) as repository:
        service = ReasoningService(repository, muse)

        def ask(question):
            try:
                answer = service.ask(args.video_id, question)
            except ReasoningError as error:
                print(f"Error: {error}", file=sys.stderr)
                return
            if args.json:
                print(json.dumps(answer.model_dump(mode="json"), indent=2))
            else:
                print_answer(answer, args.verbose)

        if args.question:
            ask(args.question)
            return
        print(f"Asking about video '{args.video_id}'. Empty line to quit.")
        while (question := input("\n> ").strip()):
            ask(question)


if __name__ == "__main__":
    main()
