"""Project an existing completed v4 campaign into static JSON; zero model calls."""
import argparse
from pathlib import Path
from searchclinic.evaluation.runtime_export import export_runtime_results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--previous', required=True, type=Path)
    parser.add_argument('--cases', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    data = export_runtime_results(args.input, args.previous, args.cases, args.output)
    print(f"Exported {len(data['pairs']) * 2} saved slots; new model calls: 0")


if __name__ == '__main__':
    main()
