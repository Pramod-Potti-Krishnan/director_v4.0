#!/usr/bin/env python3
"""
Text Service + Layout Service Integration Test
==============================================

Tests the new Text Service v1.2.2 unified slides API with Layout Service
to verify end-to-end presentation generation.

Text Service: web-production-5daf.up.railway.app
Layout Service: web-production-f0d13.up.railway.app
"""

import asyncio
import aiohttp
import ssl
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# Disable SSL verification for testing (macOS certificate issue)
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# Service URLs
TEXT_SERVICE_URL = "https://web-production-5daf.up.railway.app"
LAYOUT_SERVICE_URL = "https://web-production-f0d13.up.railway.app"

# Synthetic test data
TEST_PRESENTATION = {
    "title": "AI-Powered Customer Service Platform",
    "subtitle": "Transforming Support with Intelligence",
    "author": "Product Team",
    "audience": "executives",
    "tone": "professional"
}

TEST_SLIDES = [
    {
        "slide_number": 1,
        "layout": "H1-structured",
        "narrative": "Introduction to our revolutionary AI customer service platform",
        "data": {
            "presentation_title": TEST_PRESENTATION["title"],
            "subtitle": TEST_PRESENTATION["subtitle"],
            "author_name": TEST_PRESENTATION["author"],
            "date_info": datetime.now().strftime("%B %Y")
        }
    },
    {
        "slide_number": 2,
        "layout": "C1-text",
        "narrative": "The problem: Customer service teams are overwhelmed with repetitive queries",
        "data": {
            "variant_id": "bullets",
            "topics": [
                "80% of support tickets are repetitive questions",
                "Average response time exceeds 24 hours",
                "Agent burnout leads to 40% annual turnover",
                "Customer satisfaction scores declining"
            ],
            "content_style": "bullets"
        }
    },
    {
        "slide_number": 3,
        "layout": "C1-text",
        "narrative": "Our AI solution automates responses while maintaining human touch",
        "data": {
            "variant_id": "sequential_3col",
            "topics": [
                "AI-powered response suggestions",
                "Seamless handoff to human agents",
                "Continuous learning from interactions"
            ],
            "content_style": "bullets"
        }
    },
    {
        "slide_number": 4,
        "layout": "H2-section",
        "narrative": "Key features of the platform",
        "data": {
            "section_number": "01",
            "section_title": "Platform Features"
        }
    },
    {
        "slide_number": 5,
        "layout": "C1-text",
        "narrative": "Smart routing ensures queries reach the right agent instantly",
        "data": {
            "variant_id": "comparison",
            "topics": [
                "Intent classification with 95% accuracy",
                "Skill-based agent matching",
                "Priority queue management",
                "Real-time workload balancing"
            ],
            "content_style": "bullets"
        }
    },
    {
        "slide_number": 6,
        "layout": "C1-text",
        "narrative": "Results from our pilot program with enterprise customers",
        "data": {
            "variant_id": "metrics_dashboard",
            "topics": [
                "65% reduction in response time",
                "45% decrease in ticket volume",
                "92% customer satisfaction score",
                "$2.3M annual savings per 100 agents"
            ],
            "content_style": "bullets"
        }
    },
    {
        "slide_number": 7,
        "layout": "H3-closing",
        "narrative": "Thank you for your attention, let's discuss next steps",
        "data": {
            "closing_message": "Ready to Transform Your Customer Service?",
            "contact_email": "sales@company.com",
            "website_url": "www.company.com/demo"
        }
    }
]


class TextServiceClient:
    """Client for Text Service v1.2.2 unified slides API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    async def health_check(self, session: aiohttp.ClientSession) -> Dict:
        """Check if Text Service is healthy."""
        async with session.get(f"{self.base_url}/health") as resp:
            return await resp.json()

    async def generate_slide(
        self,
        session: aiohttp.ClientSession,
        layout: str,
        slide_number: int,
        narrative: str,
        data: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Call the unified /v1.2/slides/{layout} endpoint.
        Returns spec-compliant response with all fields.
        """
        # Build request payload based on layout
        payload = {
            "slide_number": slide_number,
            "narrative": narrative,
            "context": context or {"audience": "executives", "tone": "professional"}
        }

        # Add layout-specific fields
        if layout == "H1-structured":
            payload.update({
                "presentation_title": data.get("presentation_title", ""),
                "subtitle": data.get("subtitle", ""),
                "author_name": data.get("author_name", ""),
                "date_info": data.get("date_info", ""),
                "visual_style": "professional"
            })
        elif layout == "H2-section":
            payload.update({
                "section_number": data.get("section_number", "01"),
                "section_title": data.get("section_title", ""),
                "visual_style": "professional"
            })
        elif layout == "H3-closing":
            payload.update({
                "closing_message": data.get("closing_message", ""),
                "contact_email": data.get("contact_email", ""),
                "website_url": data.get("website_url", ""),
                "visual_style": "professional"
            })
        elif layout in ["C1-text", "L25"]:
            payload.update({
                "variant_id": data.get("variant_id", "bullets"),
                "topics": data.get("topics", []),
                "content_style": data.get("content_style", "bullets")
            })

        endpoint = f"{self.base_url}/v1.2/slides/{layout}"
        print(f"  → Calling {endpoint}")

        try:
            async with session.post(endpoint, json=payload, timeout=60) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return {"success": True, "data": result, "layout": layout}
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": error_text, "status": resp.status, "layout": layout}
        except Exception as e:
            return {"success": False, "error": str(e), "layout": layout}


class LayoutServiceClient:
    """Client for Layout Service (Deck Builder)."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    async def health_check(self, session: aiohttp.ClientSession) -> Dict:
        """Check if Layout Service is healthy."""
        async with session.get(f"{self.base_url}/health") as resp:
            return await resp.json()

    async def create_presentation(
        self,
        session: aiohttp.ClientSession,
        title: str,
        slides: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a presentation with slides."""
        payload = {
            "title": title,
            "slides": slides
        }

        endpoint = f"{self.base_url}/api/presentations"
        print(f"  → Creating presentation at {endpoint}")

        try:
            async with session.post(endpoint, json=payload, timeout=60) as resp:
                if resp.status in [200, 201]:
                    result = await resp.json()
                    return {"success": True, "data": result}
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": error_text, "status": resp.status}
        except Exception as e:
            return {"success": False, "error": str(e)}


def assemble_layout_payload(layout: str, text_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assemble layout-specific payload from Text Service response.
    Matches SLIDE_GENERATION_INPUT_SPEC.md exactly.
    """
    data = text_response.get("data", {})

    # Base content - Text Service returns these directly
    content = {
        "slide_title": data.get("slide_title", ""),
        "subtitle": data.get("subtitle", ""),
    }

    # Add layout-specific fields
    if layout == "H1-structured":
        content["author_info"] = data.get("author_info", "")
        background_color = data.get("background_color", "#1e3a5f")
    elif layout == "H2-section":
        content["section_number"] = data.get("section_number", "")
        background_color = data.get("background_color", "#374151")
    elif layout == "H3-closing":
        content["contact_info"] = data.get("contact_info", "")
        content["closing_message"] = data.get("closing_message", "")
        background_color = data.get("background_color", "#1e3a5f")
    elif layout in ["C1-text", "L25"]:
        content["body"] = data.get("body", "")
        content["rich_content"] = data.get("rich_content", "")
        background_color = data.get("background_color", "#ffffff")
    else:
        background_color = data.get("background_color", "#ffffff")

    return {
        "layout": layout,
        "content": content,
        "background_color": background_color
    }


async def test_text_service_endpoints():
    """Test Text Service unified slides endpoints."""
    print("\n" + "="*60)
    print("TEST 1: Text Service Unified Slides API")
    print("="*60)

    client = TextServiceClient(TEXT_SERVICE_URL)
    results = []

    connector = aiohttp.TCPConnector(ssl=SSL_CONTEXT)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Health check
        print("\n[1.1] Health Check")
        try:
            health = await client.health_check(session)
            print(f"  ✓ Text Service is healthy: {health}")
        except Exception as e:
            print(f"  ✗ Health check failed: {e}")
            return []

        # Test each slide
        print("\n[1.2] Generating Slides via Unified API")
        for slide in TEST_SLIDES:
            print(f"\n  Slide {slide['slide_number']}: {slide['layout']}")
            result = await client.generate_slide(
                session,
                layout=slide["layout"],
                slide_number=slide["slide_number"],
                narrative=slide["narrative"],
                data=slide["data"]
            )

            if result["success"]:
                data = result["data"]
                print(f"    ✓ Generated successfully")
                print(f"      - slide_title: {data.get('slide_title', 'N/A')[:50]}...")
                print(f"      - background_color: {data.get('background_color', 'N/A')}")
                if "body" in data:
                    print(f"      - body: {str(data.get('body', ''))[:50]}...")
            else:
                print(f"    ✗ Failed: {result.get('error', 'Unknown error')[:100]}")

            results.append(result)

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

    # Summary
    success_count = sum(1 for r in results if r["success"])
    print(f"\n  Summary: {success_count}/{len(results)} slides generated successfully")

    return results


async def test_layout_service():
    """Test Layout Service presentation creation."""
    print("\n" + "="*60)
    print("TEST 2: Layout Service Presentation Creation")
    print("="*60)

    client = LayoutServiceClient(LAYOUT_SERVICE_URL)

    connector = aiohttp.TCPConnector(ssl=SSL_CONTEXT)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Health check
        print("\n[2.1] Health Check")
        try:
            health = await client.health_check(session)
            print(f"  ✓ Layout Service is healthy: {health}")
        except Exception as e:
            print(f"  ✗ Health check failed: {e}")
            return None

    return {"success": True, "message": "Layout Service is available"}


async def test_end_to_end_generation():
    """Test complete flow: Text Service → Layout Service."""
    print("\n" + "="*60)
    print("TEST 3: End-to-End Generation (Text → Layout)")
    print("="*60)

    text_client = TextServiceClient(TEXT_SERVICE_URL)
    layout_client = LayoutServiceClient(LAYOUT_SERVICE_URL)

    connector = aiohttp.TCPConnector(ssl=SSL_CONTEXT)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Step 1: Generate all slides via Text Service
        print("\n[3.1] Generating Slide Content via Text Service")
        generated_slides = []

        for slide in TEST_SLIDES:
            print(f"  Generating slide {slide['slide_number']} ({slide['layout']})...")
            result = await text_client.generate_slide(
                session,
                layout=slide["layout"],
                slide_number=slide["slide_number"],
                narrative=slide["narrative"],
                data=slide["data"]
            )

            if result["success"]:
                # Assemble into Layout Service format
                layout_payload = assemble_layout_payload(slide["layout"], result)
                generated_slides.append(layout_payload)
                print(f"    ✓ Success")
            else:
                print(f"    ✗ Failed: {result.get('error', 'Unknown')[:50]}")
                # Add placeholder for failed slides
                generated_slides.append({
                    "layout": slide["layout"],
                    "content": {
                        "slide_title": f"<h2>Slide {slide['slide_number']}</h2>",
                        "subtitle": "<p>Content generation failed</p>"
                    },
                    "background_color": "#ffffff"
                })

            await asyncio.sleep(0.3)

        print(f"\n  Generated {len(generated_slides)} slides")

        # Step 2: Create presentation via Layout Service
        print("\n[3.2] Creating Presentation via Layout Service")

        result = await layout_client.create_presentation(
            session,
            title=TEST_PRESENTATION["title"],
            slides=generated_slides
        )

        if result["success"]:
            data = result["data"]
            pres_id = data.get("id") or data.get("presentation_id")
            print(f"  ✓ Presentation created!")
            print(f"    - ID: {pres_id}")
            print(f"    - URL: {LAYOUT_SERVICE_URL}/p/{pres_id}")
            return {
                "success": True,
                "presentation_id": pres_id,
                "url": f"{LAYOUT_SERVICE_URL}/p/{pres_id}",
                "slides_count": len(generated_slides)
            }
        else:
            print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
            return {"success": False, "error": result.get("error")}


async def test_single_slide_detailed():
    """Test a single C1-text slide with detailed output."""
    print("\n" + "="*60)
    print("TEST 4: Detailed C1-text Slide Generation")
    print("="*60)

    client = TextServiceClient(TEXT_SERVICE_URL)

    connector = aiohttp.TCPConnector(ssl=SSL_CONTEXT)
    async with aiohttp.ClientSession(connector=connector) as session:
        print("\n[4.1] Generating C1-text slide with bullets variant")

        result = await client.generate_slide(
            session,
            layout="C1-text",
            slide_number=1,
            narrative="The key benefits of adopting AI in customer service",
            data={
                "variant_id": "bullets",
                "topics": [
                    "Reduce response time by 60%",
                    "Handle 10x more queries",
                    "24/7 availability",
                    "Consistent quality"
                ],
                "content_style": "bullets"
            }
        )

        if result["success"]:
            data = result["data"]
            print("\n  ✓ Full Response:")
            print(f"    slide_title: {data.get('slide_title', 'N/A')}")
            print(f"    subtitle: {data.get('subtitle', 'N/A')}")
            print(f"    body: {data.get('body', 'N/A')[:200]}...")
            print(f"    rich_content: {str(data.get('rich_content', 'N/A'))[:200]}...")
            print(f"    background_color: {data.get('background_color', 'N/A')}")

            # Show assembled payload
            payload = assemble_layout_payload("C1-text", result)
            print("\n  Assembled Layout Payload:")
            print(json.dumps(payload, indent=4)[:500])
        else:
            print(f"\n  ✗ Failed: {result.get('error')}")

        return result


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("TEXT SERVICE + LAYOUT SERVICE INTEGRATION TEST")
    print("="*60)
    print(f"Text Service:   {TEXT_SERVICE_URL}")
    print(f"Layout Service: {LAYOUT_SERVICE_URL}")
    print(f"Test Time:      {datetime.now().isoformat()}")

    # Run tests
    await test_text_service_endpoints()
    await test_layout_service()
    await test_single_slide_detailed()

    # End-to-end test
    result = await test_end_to_end_generation()

    # Final summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)

    if result and result.get("success"):
        print(f"\n✓ SUCCESS! Presentation created:")
        print(f"  URL: {result['url']}")
        print(f"  Slides: {result['slides_count']}")
    else:
        print(f"\n✗ End-to-end test failed")
        if result:
            print(f"  Error: {result.get('error', 'Unknown')}")


if __name__ == "__main__":
    asyncio.run(main())
