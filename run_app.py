import argparse
import webbrowser


def _build_parser() -> argparse.ArgumentParser:
    import os
    env_port = int(os.getenv("PORT", 8000))
    # In cloud environments, we must bind to 0.0.0.0
    default_host = "0.0.0.0" if os.getenv("PORT") else "127.0.0.1"
    
    parser = argparse.ArgumentParser(
        description="Launch the HSCI web application (FastAPI + Dashboard UI)."
    )
    parser.add_argument("--host", default=default_host, help=f"Bind address (default: {default_host})")
    parser.add_argument("--port", type=int, default=env_port, help=f"Port number (default: {env_port})")
    
    # Disable browser launch if in cloud environment
    no_browser_default = True if os.getenv("PORT") else False
    parser.add_argument(
        "--no-browser",
        action="store_true",
        default=no_browser_default,
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
    print("HSCI Application Launcher v2.1.0 (Axiomatic)")
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
