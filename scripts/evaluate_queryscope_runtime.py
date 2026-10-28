"""Recheck saved v3 outputs without new model calls or revised primary scores."""
import argparse
import json
from pathlib import Path
from searchclinic.evaluation.runtime_audit import run_audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=Path('docs/verification/queryscope-v3/actual-api-v1/results.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run_audit(args.results, args.output)
    print(json.dumps({'summary': result['summary'], 'preparation': result['context_preparation']['summary'],
                      'max_payload_bytes': result['context_preparation']['max_payload_bytes'],
                      'all_within_request_limit': result['context_preparation']['all_within_request_limit'],
                      'new_api_calls': 0}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
