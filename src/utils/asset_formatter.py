"""
Asset Field Formatter - Ensures asset fields follow the Goal/Content/Style format.
"""
import re
from typing import Optional


class AssetFormatter:
    """Formats asset fields to ensure they follow the required Goal/Content/Style format."""
    
    @staticmethod
    def format_asset_field(value: Optional[str]) -> Optional[str]:
        """
        Convert a plain text asset description to Goal/Content/Style format.
        
        Args:
            value: The asset field value (analytics_needed, visuals_needed, or diagrams_needed)
            
        Returns:
            Formatted string with Goal/Content/Style sections, or None if input is None/empty
        """
        if not value or value.strip() == "":
            return None
            
        # Check if already in correct format
        if all(marker in value for marker in ["**Goal:**", "**Content:**", "**Style:**"]):
            return value
        
        # Parse the plain text description to extract components
        formatted = AssetFormatter._parse_and_format(value)
        return formatted
    
    @staticmethod
    def _parse_and_format(text: str) -> str:
        """
        Parse plain text and create Goal/Content/Style format.
        """
        text = text.strip()
        
        # Common patterns to identify in descriptions
        goal_keywords = ["to", "for", "that", "showing", "illustrating", "demonstrating", "proving", "highlighting"]
        content_keywords = ["chart", "graph", "diagram", "image", "photo", "icon", "visualization", "infographic", "dashboard"]
        style_keywords = ["modern", "clean", "professional", "simple", "colorful", "minimal", "animated", "3D", "realistic"]
        
        # Try to intelligently parse the text
        goal = ""
        content = ""
        style = ""
        
        # Look for chart/graph/diagram type descriptions
        if any(keyword in text.lower() for keyword in ["table", "grid", "matrix", "comparison"]):
            # Table-focused parsing
            goal = "To organize and compare information systematically"
            content = text
            style = "Clean, structured table format"
            
            # Try to extract more specific goal
            if "comparison" in text.lower():
                goal = "To compare and contrast different options or metrics"
            elif "summary" in text.lower():
                goal = "To summarize key information in a structured format"
            elif "matrix" in text.lower():
                goal = "To show relationships in a matrix format"
                
        elif any(keyword in text.lower() for keyword in ["chart", "graph", "plot", "dashboard"]):
            # Analytics-focused parsing
            goal = "To visually represent data and insights"
            content = text
            style = "Clean, professional data visualization"
            
            # Try to extract more specific goal
            if "showing" in text.lower():
                parts = text.split("showing", 1)
                if len(parts) > 1:
                    goal = f"To show {parts[1].strip()}"
                    content = parts[0].strip()
            elif "comparing" in text.lower():
                goal = "To compare and contrast data points"
            elif "trend" in text.lower():
                goal = "To illustrate trends over time"
                
        elif any(keyword in text.lower() for keyword in ["image", "photo", "picture", "graphic"]):
            # Visual-focused parsing
            goal = "To create visual impact and engagement"
            content = text
            style = "High-quality, professional imagery"
            
            # Try to extract emotional/purpose goal
            if "emotional" in text.lower():
                goal = "To create an emotional connection"
            elif "professional" in text.lower():
                goal = "To convey professionalism and credibility"
            elif "illustrat" in text.lower():
                goal = "To illustrate the concept visually"
                
        elif any(keyword in text.lower() for keyword in ["diagram", "flow", "process", "structure"]):
            # Diagram-focused parsing
            goal = "To clarify structure and relationships"
            content = text
            style = "Clear, well-organized diagram"
            
            # Try to extract specific purpose
            if "process" in text.lower():
                goal = "To illustrate the process flow"
            elif "relationship" in text.lower():
                goal = "To show relationships between elements"
            elif "structure" in text.lower():
                goal = "To demonstrate organizational structure"
        else:
            # Generic parsing
            goal = "To enhance understanding and engagement"
            content = text
            style = "Professional and appropriate to context"
        
        # Clean up extracted parts
        content = content.replace("**Goal:**", "").replace("**Content:**", "").replace("**Style:**", "")
        
        # Extract style hints from the original text
        style_matches = []
        for keyword in style_keywords:
            if keyword in text.lower():
                style_matches.append(keyword)
        
        if style_matches:
            style = f"{', '.join(style_matches).capitalize()} style"
        
        # Build the formatted string
        return f"**Goal:** {goal} **Content:** {content} **Style:** {style}"
    
    @staticmethod
    def format_slide(slide):
        """
        Format all asset fields in a slide object.
        
        Args:
            slide: A Slide object with potential asset fields
            
        Returns:
            The same slide object with formatted asset fields
        """
        # Format each asset field if present
        if hasattr(slide, 'analytics_needed') and slide.analytics_needed:
            slide.analytics_needed = AssetFormatter.format_asset_field(slide.analytics_needed)
            
        if hasattr(slide, 'visuals_needed') and slide.visuals_needed:
            slide.visuals_needed = AssetFormatter.format_asset_field(slide.visuals_needed)
            
        if hasattr(slide, 'diagrams_needed') and slide.diagrams_needed:
            slide.diagrams_needed = AssetFormatter.format_asset_field(slide.diagrams_needed)
            
        if hasattr(slide, 'tables_needed') and slide.tables_needed:
            slide.tables_needed = AssetFormatter.format_asset_field(slide.tables_needed)
            
        return slide
    
    @staticmethod
    def format_strawman(strawman):
        """
        Format all asset fields in a PresentationStrawman object.
        
        Args:
            strawman: A PresentationStrawman object
            
        Returns:
            The same strawman object with all slides' asset fields formatted
        """
        if hasattr(strawman, 'slides'):
            for slide in strawman.slides:
                AssetFormatter.format_slide(slide)
        
        return strawman