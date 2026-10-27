"""Default: dry-run only. --live also requires a separately granted approval file."""
import argparse
from pathlib import Path
from searchclinic.evaluation.llm_campaign import prepare,execute


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--prepared',type=Path)
    parser.add_argument('--approval',type=Path)
    args=parser.parse_args()
    if args.live:
        if not args.prepared or not args.approval:
            parser.error('--live requires --prepared and separately authorized --approval')
        result=execute(args.prepared,args.output,args.approval)
        print(f"actual responses={result['responses']} errors={result['errors']}")
    else:
        result=prepare(args.output)
        print(f"prepared={len(result['requests'])}; new API calls=0; approval required")

if __name__=='__main__':main()
