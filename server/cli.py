"""Command line: python -m server.cli {download,train,predict} ..."""

import argparse

import pandas as pd

from server.config import CITIES, PARSE_YEAR


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m server.cli", description="Live delivery ETA (LaDe-D).")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("download", help="Download and verify every city's delivery file and road network.")
    p = sub.add_parser("train", help="Train, evaluate, and store the live ETA model.")
    p.add_argument("--city", choices=[*CITIES, "all"], default="all")
    p = sub.add_parser("predict", help="ETAs for one courier's pending packages at a moment in time.")
    p.add_argument("--city", choices=CITIES, default="yt")
    p.add_argument("--courier", required=True, help="Raw courier id from the CSV, e.g. 75")
    p.add_argument("--at", required=True, help="Moment in source format 'MM-DD HH:MM:SS'")
    args = parser.parse_args(argv)

    if args.command == "download":
        from server.data.download import download_city, download_roads

        for city in CITIES:
            manifest = download_city(city)
            print(f"Verified {manifest['local_file']}: {manifest['row_count']:,} rows, sha256 {manifest['sha256']}")
        print(f"Roads: {', '.join(path.name for path in download_roads())}")
    elif args.command == "train":
        from server.config import CITY_SPLITS
        from server.pipeline.train import train_city

        for city in CITIES if args.city == "all" else [args.city]:
            train_city(city, CITY_SPLITS[city])
    else:
        from server.data.loading import load_city
        from server.serving.predictor import LiveETAPredictor

        records, _ = load_city(args.city)
        at = pd.Timestamp(f"{PARSE_YEAR}-{args.at}")
        result = LiveETAPredictor.from_store(args.city).predict(records, args.courier, at)
        with pd.option_context("display.width", 160, "display.max_rows", 60):
            print(result.to_string(index=False) if len(result) else "No pending packages for this courier at that time.")


if __name__ == "__main__":
    main()
