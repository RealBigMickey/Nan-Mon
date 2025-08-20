import argparse
from nanmon.game import run_game


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", type=float, default=None, nargs="?", help="Run headless for N seconds")
    args = parser.parse_args()

    while True:
        res = run_game(headless_seconds=args.headless)
        if res == "RESTART":
            continue
        break


if __name__ == "__main__":
    main()
