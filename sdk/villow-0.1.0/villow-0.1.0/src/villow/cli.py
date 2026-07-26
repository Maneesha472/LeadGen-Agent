from __future__ import annotations

import argparse
import sys
from pathlib import Path

from villow.contract_test import ContractTestCredentials, ContractTestRunner
from villow.manifest import validate_manifest


def main(argv: list[str] | None = None) -> int:
    command_argv = list(sys.argv[1:] if argv is None else argv)
    if Path(sys.argv[0]).name == "villow-contract-test" and (
        not command_argv or command_argv[0] != "contract-test"
    ):
        command_argv = ["contract-test", *command_argv]

    parser = argparse.ArgumentParser(prog="villow")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate a Villow agent manifest")
    validate.add_argument("manifest")
    contract_test = subparsers.add_parser("contract-test", help="run Villow publisher contract checks")
    contract_test.add_argument("endpoint")
    contract_test.add_argument("--signing-key-id", required=True)
    contract_test.add_argument("--publisher-id", required=True)
    contract_test.add_argument("--agent-id", required=True)
    contract_test.add_argument("--secret", required=True)
    contract_test.add_argument("--timeout-seconds", type=float, default=5.0)
    contract_test.add_argument("--offline", action="store_true", help="run signing and schema checks without network calls")
    args = parser.parse_args(command_argv)

    if args.command == "validate":
        result = validate_manifest(args.manifest)
        for warning in result.warnings:
            print(f"warning: {warning}")
        if result.valid:
            print(f"valid: {args.manifest}")
            return 0
        for error in result.errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    if args.command == "contract-test":
        report = ContractTestRunner(
            endpoint=args.endpoint,
            credentials=ContractTestCredentials(
                publisher_id=args.publisher_id,
                agent_id=args.agent_id,
                signing_key_id=args.signing_key_id,
                secret=args.secret,
            ),
            timeout_seconds=args.timeout_seconds,
            offline=args.offline,
        ).run()
        print(report.to_json())
        return 0 if report.passed else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
