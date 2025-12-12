"""
Layout Schema Manager for Director Agent v3.2
==============================================

Single source of truth for layout requirements, schemas, and best use cases.
Replaces rule-based LayoutMapper with schema-driven architecture.
"""

import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from src.models.agents import Slide
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class LayoutSchemaManager:
    """
    Manages layout schemas for schema-driven content generation.

    Responsibilities:
    - Load and cache layout schemas from JSON
    - Provide schema specifications for each layout
    - Build structured content requests
    - Validate generated content against schemas
    - Format layout options for AI selection
    """

    def __init__(self):
        """Initialize layout schema manager and load schemas."""
        self.schemas = self._load_schemas()
        logger.info(f"LayoutSchemaManager initialized with {len(self.schemas)} layouts")

    def _load_schemas(self) -> Dict[str, Any]:
        """
        Load layout schemas from JSON file.

        Returns:
            Dictionary of layout schemas keyed by layout_id
        """
        # Get path to layout_schemas.json
        base_dir = Path(__file__).parent.parent.parent
        schema_file = base_dir / 'config' / 'deck_builder' / 'layout_schemas.json'

        if not schema_file.exists():
            raise FileNotFoundError(f"Layout schemas file not found: {schema_file}")

        with open(schema_file, 'r') as f:
            data = json.load(f)

        return data['layouts']

    def get_schema(self, layout_id: str) -> Dict[str, Any]:
        """
        Get complete schema for a specific layout.

        Args:
            layout_id: Layout ID (e.g., "L07")

        Returns:
            Complete layout schema dictionary

        Raises:
            ValueError: If layout_id not found
        """
        if layout_id not in self.schemas:
            raise ValueError(f"Unknown layout ID: {layout_id}")

        return self.schemas[layout_id]

    def get_content_schema(self, layout_id: str) -> Dict[str, Any]:
        """
        Get just the content_schema portion for a layout.

        Args:
            layout_id: Layout ID (e.g., "L07")

        Returns:
            Content schema dictionary with field specifications
        """
        schema = self.get_schema(layout_id)
        return schema['content_schema']

    def get_all_layouts_with_use_cases(self) -> List[Dict[str, Any]]:
        """
        Get all layouts with their best use cases for AI selection.

        Returns:
            List of layout dictionaries with id, name, best_use_case, keywords
        """
        layouts = []
        for layout_id, schema in self.schemas.items():
            layouts.append({
                'layout_id': layout_id,
                'name': schema['name'],
                'slide_subtype': schema['slide_subtype'],
                'best_use_case': schema['best_use_case'],
                'best_for_keywords': schema['best_for_keywords'],
                'content_fields': list(schema['content_schema'].keys())
            })
        return layouts

    def build_content_request(
        self,
        layout_id: str,
        slide: Slide,
        presentation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build structured content generation request for Text Service.

        Args:
            layout_id: Selected layout ID
            slide: Slide object with narrative, key_points, etc.
            presentation_context: Overall presentation context

        Returns:
            Structured request dictionary for Text Service with format specifications
        """
        schema = self.get_schema(layout_id)
        content_schema = schema['content_schema']

        # Build content guidance from slide
        content_guidance = {
            'title': slide.title,
            'narrative': slide.narrative or '',
            'key_points': slide.key_points or [],
            'slide_type': slide.slide_type,
            'analytics_needed': slide.analytics_needed,
            'visuals_needed': slide.visuals_needed,
            'diagrams_needed': slide.diagrams_needed,
            'tables_needed': slide.tables_needed
        }

        # Add presentation context if provided
        if presentation_context:
            content_guidance['presentation_context'] = presentation_context

        # Extract format specifications for each field (v3.2 format ownership)
        # This ensures Text Service knows which fields need plain_text vs html
        field_specs = self._extract_field_specifications(content_schema)

        # Build structured request
        request = {
            'layout_id': layout_id,
            'layout_name': schema['name'],
            'layout_subtype': schema['slide_subtype'],
            'layout_schema': content_schema,
            'field_specifications': field_specs,  # v3.2: Format ownership specs
            'content_guidance': content_guidance,
            'slide_id': slide.slide_id,
            'slide_number': slide.slide_number
        }

        return request

    def _extract_field_specifications(self, content_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract format specifications from content schema for Text Service.

        Recursively extracts format_type, format_owner, validation_threshold,
        and expected_structure from all fields including nested structures.

        Args:
            content_schema: Content schema from layout

        Returns:
            Dictionary mapping field names to their format specifications
        """
        field_specs = {}

        for field_name, field_spec in content_schema.items():
            # Extract format specs for this field
            spec = {}

            # Core format specifications (v3.2)
            if 'format_type' in field_spec:
                spec['format_type'] = field_spec['format_type']
            if 'format_owner' in field_spec:
                spec['format_owner'] = field_spec['format_owner']
            if 'validation_threshold' in field_spec:
                spec['validation_threshold'] = field_spec['validation_threshold']
            if 'expected_structure' in field_spec:
                spec['expected_structure'] = field_spec['expected_structure']

            # Include constraints for validation
            if 'max_chars' in field_spec:
                spec['max_chars'] = field_spec['max_chars']
            if 'max_words' in field_spec:
                spec['max_words'] = field_spec['max_words']
            if 'max_lines' in field_spec:
                spec['max_lines'] = field_spec['max_lines']
            if 'min_items' in field_spec:
                spec['min_items'] = field_spec['min_items']
            if 'max_items' in field_spec:
                spec['max_items'] = field_spec['max_items']
            if 'max_chars_per_item' in field_spec:
                spec['max_chars_per_item'] = field_spec['max_chars_per_item']

            # Include field type for context
            if 'type' in field_spec:
                spec['type'] = field_spec['type']

            # Add to field_specs if we found format specifications
            if spec:
                field_specs[field_name] = spec

            # Handle nested structures (array_of_objects, objects)
            if 'item_structure' in field_spec:
                # array_of_objects (e.g., L06 numbered_items, L19 metrics)
                nested_specs = {}
                for nested_field, nested_spec in field_spec['item_structure'].items():
                    nested_field_spec = {}

                    if 'format_type' in nested_spec:
                        nested_field_spec['format_type'] = nested_spec['format_type']
                    if 'format_owner' in nested_spec:
                        nested_field_spec['format_owner'] = nested_spec['format_owner']
                    if 'validation_threshold' in nested_spec:
                        nested_field_spec['validation_threshold'] = nested_spec['validation_threshold']
                    if 'expected_structure' in nested_spec:
                        nested_field_spec['expected_structure'] = nested_spec['expected_structure']
                    if 'max_chars' in nested_spec:
                        nested_field_spec['max_chars'] = nested_spec['max_chars']
                    if 'max_lines' in nested_spec:
                        nested_field_spec['max_lines'] = nested_spec['max_lines']

                    if nested_field_spec:
                        nested_specs[nested_field] = nested_field_spec

                if nested_specs:
                    field_specs[field_name]['item_structure'] = nested_specs

            if 'structure' in field_spec:
                # object (e.g., L20 left_content/right_content)
                nested_specs = {}
                for nested_field, nested_spec in field_spec['structure'].items():
                    nested_field_spec = {}

                    if 'format_type' in nested_spec:
                        nested_field_spec['format_type'] = nested_spec['format_type']
                    if 'format_owner' in nested_spec:
                        nested_field_spec['format_owner'] = nested_spec['format_owner']
                    if 'validation_threshold' in nested_spec:
                        nested_field_spec['validation_threshold'] = nested_spec['validation_threshold']
                    if 'expected_structure' in nested_spec:
                        nested_field_spec['expected_structure'] = nested_spec['expected_structure']
                    if 'max_chars' in nested_spec:
                        nested_field_spec['max_chars'] = nested_spec['max_chars']
                    if 'max_lines' in nested_spec:
                        nested_field_spec['max_lines'] = nested_spec['max_lines']

                    if nested_field_spec:
                        nested_specs[nested_field] = nested_field_spec

                if nested_specs:
                    field_specs[field_name]['structure'] = nested_specs

        return field_specs

    def validate_content(self, layout_id: str, content: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate generated content against layout schema.

        Args:
            layout_id: Layout ID
            content: Generated content dictionary

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        schema = self.get_content_schema(layout_id)
        errors = []

        # Check required fields
        for field_name, field_spec in schema.items():
            if field_spec.get('required', False) and field_name not in content:
                errors.append(f"Missing required field: {field_name}")

        # Check field types and constraints
        for field_name, field_value in content.items():
            if field_name not in schema:
                errors.append(f"Unexpected field: {field_name}")
                continue

            field_spec = schema[field_name]
            field_type = field_spec['type']

            # Type validation
            if field_type == 'string':
                if not isinstance(field_value, str):
                    errors.append(f"Field {field_name} must be string, got {type(field_value).__name__}")
                elif 'max_chars' in field_spec and len(field_value) > field_spec['max_chars']:
                    errors.append(
                        f"Field {field_name} exceeds max_chars: {len(field_value)} > {field_spec['max_chars']}"
                    )

            elif field_type == 'array':
                if not isinstance(field_value, list):
                    errors.append(f"Field {field_name} must be array, got {type(field_value).__name__}")
                elif 'max_items' in field_spec and len(field_value) > field_spec['max_items']:
                    errors.append(
                        f"Field {field_name} exceeds max_items: {len(field_value)} > {field_spec['max_items']}"
                    )
                elif 'min_items' in field_spec and len(field_value) < field_spec['min_items']:
                    errors.append(
                        f"Field {field_name} below min_items: {len(field_value)} < {field_spec['min_items']}"
                    )

                # Validate array items
                if isinstance(field_value, list) and 'max_chars_per_item' in field_spec:
                    for idx, item in enumerate(field_value):
                        if isinstance(item, str) and len(item) > field_spec['max_chars_per_item']:
                            errors.append(
                                f"Field {field_name}[{idx}] exceeds max_chars_per_item: "
                                f"{len(item)} > {field_spec['max_chars_per_item']}"
                            )

            elif field_type == 'array_of_objects':
                if not isinstance(field_value, list):
                    errors.append(f"Field {field_name} must be array, got {type(field_value).__name__}")
                elif 'max_items' in field_spec and len(field_value) > field_spec['max_items']:
                    errors.append(
                        f"Field {field_name} exceeds max_items: {len(field_value)} > {field_spec['max_items']}"
                    )

                # Validate object structure
                if isinstance(field_value, list) and 'item_structure' in field_spec:
                    item_structure = field_spec['item_structure']
                    for idx, item in enumerate(field_value):
                        if not isinstance(item, dict):
                            errors.append(f"Field {field_name}[{idx}] must be object")
                            continue

                        # Check required keys in item structure
                        for key, key_spec in item_structure.items():
                            if key not in item:
                                errors.append(f"Field {field_name}[{idx}] missing key: {key}")
                            elif 'max_chars' in key_spec and isinstance(item[key], str):
                                if len(item[key]) > key_spec['max_chars']:
                                    errors.append(
                                        f"Field {field_name}[{idx}].{key} exceeds max_chars: "
                                        f"{len(item[key])} > {key_spec['max_chars']}"
                                    )

            elif field_type == 'object':
                if not isinstance(field_value, dict):
                    errors.append(f"Field {field_name} must be object, got {type(field_value).__name__}")

                # Validate object structure
                if isinstance(field_value, dict) and 'structure' in field_spec:
                    structure = field_spec['structure']
                    for key, key_spec in structure.items():
                        if key not in field_value:
                            errors.append(f"Field {field_name} missing key: {key}")
                        elif isinstance(key_spec, dict) and 'max_chars' in key_spec:
                            if isinstance(field_value[key], str) and len(field_value[key]) > key_spec['max_chars']:
                                errors.append(
                                    f"Field {field_name}.{key} exceeds max_chars: "
                                    f"{len(field_value[key])} > {key_spec['max_chars']}"
                                )

        is_valid = len(errors) == 0
        return is_valid, errors

    def format_layout_options_for_ai(self, exclude_layout_ids: Optional[List[str]] = None) -> str:
        """
        Format all layout options as text for AI selection prompt.

        Args:
            exclude_layout_ids: Optional list of layout IDs to exclude (e.g., ["L01", "L02", "L03"])

        Returns:
            Formatted string describing all available layouts
        """
        layouts = self.get_all_layouts_with_use_cases()

        # Filter out excluded layouts
        if exclude_layout_ids:
            layouts = [l for l in layouts if l['layout_id'] not in exclude_layout_ids]

        formatted_lines = []
        for layout in layouts:
            formatted_lines.append(f"""
**{layout['layout_id']} - {layout['name']}** ({layout['slide_subtype']})
Best Use Case: {layout['best_use_case']}
Keywords: {', '.join(layout['best_for_keywords'][:5])}
Content Fields: {', '.join(layout['content_fields'])}
""")

        return '\n'.join(formatted_lines)

    def get_layout_by_keywords(self, search_terms: List[str]) -> List[str]:
        """
        Find layouts matching specific keywords (utility method).

        Args:
            search_terms: List of search terms to match against keywords

        Returns:
            List of matching layout IDs
        """
        matching_layouts = []

        for layout_id, schema in self.schemas.items():
            keywords = schema.get('best_for_keywords', [])
            keyword_text = ' '.join(keywords).lower()

            # Check if any search term matches
            for term in search_terms:
                if term.lower() in keyword_text:
                    matching_layouts.append(layout_id)
                    break

        return matching_layouts

    def reload_schemas(self):
        """Reload schemas from JSON file (for development/testing)."""
        self.schemas = self._load_schemas()
        logger.info(f"Schemas reloaded: {len(self.schemas)} layouts")


# Singleton instance for easy access
_schema_manager_instance = None


def get_schema_manager() -> LayoutSchemaManager:
    """
    Get singleton instance of LayoutSchemaManager.

    Returns:
        LayoutSchemaManager instance
    """
    global _schema_manager_instance
    if _schema_manager_instance is None:
        _schema_manager_instance = LayoutSchemaManager()
    return _schema_manager_instance
