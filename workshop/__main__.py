"""Serve the app or rehearse the same HTTP workflow against any demo instance."""
import argparse
from functools import partial
import json
import logging
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

from dotenv import load_dotenv


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def call(base, path, *, payload=None, expect=200):
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(base.rstrip("/") + path, data=data, headers={"Content-Type": "application/json"})
    if token := os.getenv("WORKSHOP_TOKEN"):
        target = urlsplit(base)
        if target.scheme != "https" and target.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Use HTTPS when sending a presenter token to a remote endpoint.")
        request.add_header("Authorization", f"Bearer {token}")
    try:
        response = build_opener(NoRedirect).open(request, timeout=25)
    except HTTPError as exc:
        response = exc
    with response:
        result = json.load(response)
        if response.status != expect:
            raise RuntimeError(f"{path}: expected HTTP {expect}, got {response.status} ({result})")
        return result, response.headers.get("X-Request-ID")


def rehearse(base):
    health, _ = call(base, "/health")
    print(f"1. Máy chủ hoạt động | chế độ {health['mode']}")
    answer, request_id = call(base, "/chat", payload={"message": "Phiếu hỗ trợ mới có trạng thái gì?"})
    if answer.get("kind") != "answer" or "ticket-policy" not in answer["sources"] or "pending" not in answer["answer"].lower():
        raise RuntimeError(f"Unexpected FAQ response: {answer}")
    print(f"2. Hỏi đáp: {answer['answer']} | nguồn: {', '.join(answer['sources'])} | mã yêu cầu: {request_id}")

    for approve in (False, True):
        proposal, _ = call(base, "/chat", payload={"message": "Tạo phiếu hỗ trợ cho lỗi đăng nhập VPN"})
        if proposal.get("kind") != "approval_required":
            raise RuntimeError(f"Expected an approval proposal: {proposal}")
        approval_id = proposal["approval_id"]
        ticket_path = f"/tickets/{approval_id}"
        decision_path = f"/approvals/{approval_id}"
        call(base, ticket_path, expect=404)
        print(f"{5 if approve else 3}. Đề xuất (chưa tạo phiếu): {proposal['draft']['content']}")
        decision, _ = call(base, decision_path, payload={"approve": approve})
        if not approve:
            if decision != {"status": "denied"}:
                raise RuntimeError(f"Expected denial: {decision}")
            call(base, ticket_path, expect=404)
            print("4. Đã từ chối; chưa tạo phiếu.")
            continue
        ticket, request_id = call(base, ticket_path)
        repeated, _ = call(base, decision_path, payload={"approve": True})
        if decision.get("status") != "approved" or repeated != decision or ticket["status"] != "Pending":
            raise RuntimeError(f"Unexpected ticket or replay: {ticket}, {repeated}")
        print(f"6. Đã duyệt, chỉ tạo một lần: {ticket['ticket_id']} | {ticket['status']} | mã yêu cầu: {request_id}")
    print("ĐẠT: toàn bộ kịch bản diễn tập")


def load_local_env(path: Path | None = None):
    """Load optional local settings without overriding explicit process variables."""
    load_dotenv(dotenv_path=path or Path(__file__).resolve().parents[1] / ".env",
                override=False)


def serve():
    load_local_env()
    import uvicorn

    from .agent_runtime import create_app
    from .tools import demo_turn, live_turn

    host = os.getenv("WORKSHOP_HOST", "127.0.0.1")
    port = int(os.getenv("WORKSHOP_PORT", "8000"))
    mode = os.getenv("WORKSHOP_MODE", "demo")
    hosted = os.getenv("WORKSHOP_HOSTED", "0") == "1"
    factory = demo_turn
    if mode == "live":
        required = ("OPENAI_API_KEY", "WORKSHOP_CHAT_MODEL", "WORKSHOP_EMBEDDING_MODEL")
        if any(not os.getenv(name) for name in required):
            raise ValueError("Live mode requires " + ", ".join(required))
        factory = partial(live_turn, chat_model=os.environ["WORKSHOP_CHAT_MODEL"],
                          embedding_model=os.environ["WORKSHOP_EMBEDDING_MODEL"],
                          api_key=os.environ["OPENAI_API_KEY"])
    elif mode != "demo":
        raise ValueError("WORKSHOP_MODE must be demo or live.")
    app = create_app(Path(os.getenv("WORKSHOP_DB", "data/workshop.db")),
                     token=os.getenv("WORKSHOP_TOKEN"), hosted=hosted,
                     mode=mode, turn_factory=factory)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # Keep dependency logs (including request URLs) out of the presenter log.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    uvicorn.run(app, host=host, port=port, access_log=False,
                limit_concurrency=int(os.getenv("WORKSHOP_CONCURRENCY", "16")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve")
    commands.add_parser("health")
    demo = commands.add_parser("demo")
    demo.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    try:
        if args.command == "serve":
            serve()
        elif args.command == "health":
            port = int(os.getenv("WORKSHOP_PORT", "8000"))
            # Health is unauthenticated and does not need to read the token.
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                if response.status != 200:
                    raise RuntimeError("Unhealthy server.")
        else:
            rehearse(args.url)
    except (ValueError, RuntimeError, URLError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
