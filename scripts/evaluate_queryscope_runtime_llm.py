"""Prepare the frozen v4 inputs for free; --live needs a new exact approval."""
import argparse
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--live', action='store_true')
    mode.add_argument('--validate-only', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--approval', type=Path)
    args = parser.parse_args(argv)
    if args.live and not all((args.output, args.prepared, args.approval)):
        parser.error('--live requires --output, --prepared and a separately granted --approval')
    if args.validate_only and not args.prepared:
        parser.error('--validate-only requires --prepared')
    if not args.live and not args.validate_only and not args.output:
        parser.error('free preparation requires --output')

    from searchclinic.evaluation.runtime_campaign import (
        prepare_runtime_campaign, validate_runtime_preparation, execute_runtime_campaign,
    )
    if args.live:
        result = execute_runtime_campaign(args.prepared, args.output, args.approval)
        print(f"actual responses={result['responses']} errors={result['errors']}")
    elif args.validate_only:
        result = validate_runtime_preparation(args.prepared)
        print(f"validated={len(result['requests'])}; new API calls=0; approval not implied")
    else:
        result = prepare_runtime_campaign(args.output)
        print(f"prepared={len(result['requests'])}; new API calls=0; separate paid approval required")


if __name__ == '__main__':
    main()
