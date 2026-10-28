"""Export a compact static projection of an already computed runtime audit."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        raise ValueError('source_and_export_must_differ')
    report = json.loads(args.input.read_text(encoding='utf-8'))
    if report['mode'] != 'retrospective_runtime_audit' or report['new_api_calls'] != 0:
        raise ValueError('offline_runtime_audit_required')
    rows = []
    for original in report['rows']:
        row = {k: v for k, v in original.items() if k != 'runtime_answer'}
        row['runtime_effect'] = {k: v for k, v in row['runtime_effect'].items()
                                 if k in {'status', 'gate', 'semantic_support'}}
        rows.append(row)
    fields = {'case_id', 'condition', 'context', 'prior_document_ids', 'runtime_document_ids'}
    data = {'source_sha256': report['source_sha256'], 'new_api_calls': 0,
            'summary': report['summary'], 'rows': rows,
            'accepted_unique_queries': len({r['query'] for r in rows
                if r['runtime_effect'].get('gate', {}).get('accepted')}),
            'retrieval_summary': report['context_preparation']['summary'],
            'prepared': [{k: v for k, v in r.items() if k in fields}
                         for r in report['context_preparation']['rows']]}
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
