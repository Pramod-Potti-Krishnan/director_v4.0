#!/usr/bin/env python3
"""
Director Agent E2E Test - Automated Stage 6 Request Capture

This test:
1. Connects to Director via WebSocket
2. Sends a presentation request
3. Automatically responds to action prompts to drive through all stages
4. Waits for Stage 6 (content generation) to complete
5. Checks debug_captures/ for captured Text Service requests

Usage:
    # Test against local Director (must be running on port 8000)
    python tools/test_director_e2e.py --local

    # Test against Railway Director
    python tools/test_director_e2e.py --url wss://your-director.up.railway.app

After the test, run:
    python tools/compare_stage6_requests.py
"""

import asyncio
import websockets
import json
import ssl
import uuid
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# ANSI colors
COLORS = {
    'reset': '\033[0m',
    'red': '\033[91m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'blue': '\033[94m',
    'magenta': '\033[95m',
    'cyan': '\033[96m',
    'gray': '\033[90m',
    'bold': '\033[1m',
}

def color(text, color_name):
    return f"{COLORS.get(color_name, '')}{text}{COLORS['reset']}"

def timestamp():
    return datetime.now().strftime("%H:%M:%S")


class DirectorE2ETest:
    """Automated Director end-to-end test."""

    def __init__(self, ws_url: str, session_id: str = None):
        self.ws_url = ws_url
        self.session_id = session_id or f"e2e-test-{uuid.uuid4().hex[:8]}"
        self.user_id = "e2e-test-user"
        self.ws = None
        self.completed = False
        self.presentation_url = None
        self.slides_received = False
        self.stage6_started = False
        self.messages_received = []

        # Test configuration
        self.presentation_topic = "The Story of Hanuman - a mythological tale for kids"
        self.auto_accept = True  # Auto-accept all action prompts
        self.qa_responses_sent = 0
        self.max_qa_responses = 3  # Limit follow-up responses

        # Pre-configured answers to common Director questions
        self.qa_answers = [
            "The audience is children aged 6-10. Duration is 10 minutes. Purpose is educational storytelling. The presentation should be fun, colorful, and engaging with simple language.",
            "Yes, that looks good. Please proceed.",
            "Yes, I approve this plan. Let's generate the presentation."
        ]

    async def connect(self):
        """Connect to Director WebSocket."""
        full_url = f"{self.ws_url}/ws?session_id={self.session_id}&user_id={self.user_id}"

        print(color(f"[{timestamp()}] Connecting to: {full_url}", 'cyan'))

        # SSL context for wss://
        ssl_context = None
        if self.ws_url.startswith("wss://"):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        self.ws = await websockets.connect(
            full_url,
            ssl=ssl_context,
            ping_interval=30,
            ping_timeout=10
        )
        print(color(f"[{timestamp()}] Connected!", 'green'))

    async def send_message(self, text: str):
        """Send a user message to Director."""
        msg = {
            "type": "user_message",
            "data": {"text": text}
        }
        await self.ws.send(json.dumps(msg))
        print(color(f"[{timestamp()}] >>> SENT: {text}", 'cyan'))

    async def send_action_response(self, value: str):
        """Send an action response to Director."""
        msg = {
            "type": "action_response",
            "data": {"value": value}
        }
        await self.ws.send(json.dumps(msg))
        print(color(f"[{timestamp()}] >>> ACTION: {value}", 'yellow'))

    async def handle_message(self, data: dict):
        """Handle incoming messages from Director."""
        msg_type = data.get('type', 'unknown')
        payload = data.get('payload', {})
        self.messages_received.append(data)

        if msg_type == 'chat_message':
            text = payload.get('text', '')
            print(color(f"[{timestamp()}] CHAT: {text[:200]}...", 'green'))

            # Auto-respond to questions if enabled
            if self.auto_accept and '?' in text and self.qa_responses_sent < self.max_qa_responses:
                await asyncio.sleep(2)  # Brief delay
                response = self.qa_answers[min(self.qa_responses_sent, len(self.qa_answers) - 1)]
                self.qa_responses_sent += 1
                await self.send_message(response)

        elif msg_type == 'action_request':
            prompt = payload.get('prompt_text', '')
            actions = payload.get('actions', [])
            print(color(f"[{timestamp()}] ACTION PROMPT: {prompt}", 'yellow'))
            for action in actions:
                label = action.get('label', '')
                value = action.get('value', '')
                primary = action.get('primary', False)
                marker = '*' if primary else ' '
                print(f"    {marker} [{value}] {label}")

            # Auto-respond if enabled
            if self.auto_accept and actions:
                # Find primary action or use first one
                primary_action = next((a for a in actions if a.get('primary')), actions[0])
                value = primary_action.get('value', '')
                await asyncio.sleep(1)  # Brief delay to simulate user
                await self.send_action_response(value)

        elif msg_type == 'slide_update':
            slides = payload.get('slides', [])
            metadata = payload.get('metadata', {})
            title = metadata.get('main_title', 'Untitled')
            print(color(f"[{timestamp()}] SLIDES: {len(slides)} slides - '{title}'", 'blue'))
            self.slides_received = True

        elif msg_type == 'status_update':
            status = payload.get('status', '')
            text = payload.get('text', '')
            progress = payload.get('progress')

            # Detect Stage 6
            if 'content' in text.lower() or 'generating' in status.lower():
                self.stage6_started = True
                print(color(f"[{timestamp()}] STATUS: [{status}] {text} (Stage 6 detected!)", 'magenta'))
            else:
                print(color(f"[{timestamp()}] STATUS: [{status}] {text}", 'gray'))

        elif msg_type == 'presentation_url':
            self.presentation_url = payload.get('url', '')
            slide_count = payload.get('slide_count', 0)
            print(color(f"[{timestamp()}] PRESENTATION READY: {self.presentation_url}", 'green'))
            print(color(f"    Slides: {slide_count}", 'green'))
            self.completed = True

        elif msg_type == 'sync_response':
            action = payload.get('action', '')
            state = payload.get('current_state', '')
            print(color(f"[{timestamp()}] SYNC: {action} (state: {state})", 'gray'))

        else:
            print(color(f"[{timestamp()}] {msg_type.upper()}: {str(payload)[:100]}", 'gray'))

    async def run_test(self, timeout_seconds: int = 300):
        """Run the E2E test."""
        print(color("=" * 70, 'bold'))
        print(color("Director E2E Test - Stage 6 Request Capture", 'bold'))
        print(color("=" * 70, 'bold'))
        print(f"Session ID: {color(self.session_id, 'cyan')}")
        print(f"Topic: {color(self.presentation_topic, 'cyan')}")
        print(f"Auto-accept: {color(str(self.auto_accept), 'yellow')}")
        print(color("-" * 70, 'gray'))

        try:
            await self.connect()

            # Start receiving messages
            receive_task = asyncio.create_task(self.receive_loop())

            # Wait a moment for welcome message
            await asyncio.sleep(2)

            # Send initial request
            await self.send_message(self.presentation_topic)

            # Wait for completion or timeout
            start_time = asyncio.get_event_loop().time()
            while not self.completed:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout_seconds:
                    print(color(f"\n[{timestamp()}] TIMEOUT after {timeout_seconds}s", 'red'))
                    break
                await asyncio.sleep(1)

            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass

        except Exception as e:
            print(color(f"\n[{timestamp()}] ERROR: {e}", 'red'))
            import traceback
            traceback.print_exc()

        finally:
            if self.ws:
                await self.ws.close()

        # Summary
        print(color("\n" + "=" * 70, 'bold'))
        print(color("TEST SUMMARY", 'bold'))
        print(color("=" * 70, 'bold'))
        print(f"Messages received: {len(self.messages_received)}")
        print(f"Slides received: {self.slides_received}")
        print(f"Stage 6 started: {self.stage6_started}")
        print(f"Completed: {self.completed}")
        if self.presentation_url:
            print(f"Presentation URL: {color(self.presentation_url, 'green')}")

        # Check debug captures
        self.check_debug_captures()

    async def receive_loop(self):
        """Receive messages from WebSocket."""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError:
                    print(color(f"[{timestamp()}] RAW: {message[:200]}", 'gray'))
        except websockets.ConnectionClosed:
            print(color(f"\n[{timestamp()}] Connection closed", 'yellow'))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(color(f"\n[{timestamp()}] Receive error: {e}", 'red'))

    def check_debug_captures(self):
        """Check if debug captures were created."""
        debug_dir = Path(__file__).parent.parent / "debug_captures"

        print(color("\n" + "-" * 70, 'gray'))
        print(color("DEBUG CAPTURES", 'bold'))
        print(color("-" * 70, 'gray'))

        if not debug_dir.exists():
            print(color("No debug_captures/ directory found.", 'yellow'))
            print("If running against local Director, debug captures should be created.")
            print("If running against Railway, captures are on the server.")
            return

        captures = sorted(debug_dir.glob("*.json"))
        if not captures:
            print(color("No capture files found.", 'yellow'))
            return

        # Filter to recent captures (within last 5 minutes)
        recent_captures = []
        cutoff = datetime.now().timestamp() - 300  # 5 minutes ago

        for f in captures:
            if f.stat().st_mtime > cutoff:
                recent_captures.append(f)

        print(f"Total captures: {len(captures)}")
        print(f"Recent captures (last 5 min): {len(recent_captures)}")

        for f in recent_captures:
            print(f"  - {f.name}")

        if recent_captures:
            print(color("\nRun comparison script:", 'cyan'))
            print("  python tools/compare_stage6_requests.py")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Director E2E Test")
    parser.add_argument("--local", action="store_true", help="Test against local Director (localhost:8000)")
    parser.add_argument("--url", default=None, help="WebSocket URL (e.g., wss://director.up.railway.app)")
    parser.add_argument("--session", default=None, help="Session ID (auto-generated if not provided)")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds (default: 300)")
    parser.add_argument("--no-auto", action="store_true", help="Disable auto-accept for action prompts")
    args = parser.parse_args()

    # Determine URL
    if args.local:
        ws_url = "ws://localhost:8000"
    elif args.url:
        ws_url = args.url
    else:
        # Default to Railway Director v4
        ws_url = "wss://directorv33-production.up.railway.app"
        print(color("Using default Railway URL. Use --local for local testing.", 'yellow'))

    test = DirectorE2ETest(ws_url, args.session)
    test.auto_accept = not args.no_auto
    await test.run_test(args.timeout)


if __name__ == "__main__":
    asyncio.run(main())
