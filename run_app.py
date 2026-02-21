import argparse
import webbrowser


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch the HSCI web application (FastAPI + Dashboard UI)."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the dashboard in a browser.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    banner = "=" * 58
    url = f"http://{args.host}:{args.port}"

    print(banner)
    print("HSCI Application Launcher")
    print(banner)
    print(f"Dashboard URL: {url}")

    if not args.no_browser:
        try:
            webbrowser.open(url)
            print("Browser launch requested.")
        except Exception as exc:
            print(f"Could not launch browser automatically: {exc}")

    try:
        import uvicorn
    except Exception as exc:
        print("Missing dependency: uvicorn")
        print("Install it with: pip install uvicorn fastapi")
        print(f"Details: {exc}")
        return 1

    try:
        uvicorn.run(
            "brain_api:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info",
        )
        return 0
    except KeyboardInterrupt:
        print("\nShutting down HSCI application.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
