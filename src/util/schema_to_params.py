import inspect
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, create_model
from pydantic_ai import RunContext

from mcp_demo.deps import AgentDeps


def convert_schema_to_params(schema: Dict[str, Any]) -> List[inspect.Parameter]:
    # Extract properties from schema
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    # Initialise parameters list with the run context parameter
    parameters: list[inspect.Parameter] = [
        inspect.Parameter(name="ctx", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=RunContext[AgentDeps])
    ]

    for param_name, param_info in properties.items():
        param_type_str = param_info.get("type", "string")

        if param_type_str == "object":
            # Create a Pydantic model for this object parameter
            param_type = create_pydantic_model_from_schema(param_info, model_name=param_name.capitalize())

        elif param_type_str == "array":
            # Handle arrays with proper item types
            items = param_info.get("items", {})
            items_type = items.get("type", "string")

            if items_type == "object":
                # Array of objects - create a nested model for the items
                item_model = create_pydantic_model_from_schema(items, model_name=f"{param_name.capitalize()}Item")
                param_type = List[item_model]
            else:
                # Array of primitive types
                item_python_type = TYPE_MAP.get(items_type, Any)
                param_type = List[item_python_type]
        else:
            # Handle primitive types
            param_type = TYPE_MAP.get(param_type_str, Any)

        # Add parameter to the function signature
        if param_name in required:
            parameters.append(
                inspect.Parameter(name=param_name, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=param_type)
            )
        else:
            # Optional parameters get a default value of None
            parameters.append(
                inspect.Parameter(
                    name=param_name, kind=inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None, annotation=param_type
                )
            )

    return parameters


def create_pydantic_model_from_schema(schema: Dict[str, Any], model_name: str) -> type[BaseModel]:
    """
    Create a Pydantic model from a JSON schema.

    Args:
        schema: A JSON schema describing the model
        model_name: Name for the model

    Returns:
        A Pydantic model class
    """
    # Extract properties and required fields
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    # Create field definitions for Pydantic model
    fields = {}

    for field_name, field_info in properties.items():
        field_type = field_info.get("type", "string")
        description = field_info.get("description", "")

        # Handle different field types
        if field_type == "object":
            # Recursively create nested models for objects
            nested_model = create_pydantic_model_from_schema(
                field_info, model_name=f"{model_name}_{field_name.capitalize()}"
            )
            if field_name in required:
                fields[field_name] = (nested_model, Field(description=description))
            else:
                fields[field_name] = (Optional[nested_model], Field(default=None, description=description))

        elif field_type == "array":
            # Handle arrays with proper item types
            items = field_info.get("items", {})
            items_type = items.get("type", "string")

            if items_type == "object":
                # Array of objects - create a nested model for the items
                item_model = create_pydantic_model_from_schema(
                    items, model_name=f"{model_name}_{field_name.capitalize()}Item"
                )
                if field_name in required:
                    fields[field_name] = (List[item_model], Field(description=description))
                else:
                    fields[field_name] = (Optional[List[item_model]], Field(default=None, description=description))
            else:
                # Array of primitive types
                item_python_type = TYPE_MAP.get(items_type, Any)
                if field_name in required:
                    fields[field_name] = (List[item_python_type], Field(description=description))
                else:
                    fields[field_name] = (
                        Optional[List[item_python_type]],
                        Field(default=None, description=description),
                    )
        else:
            # Handle primitive types
            python_type = TYPE_MAP.get(field_type, Any)
            if field_name in required:
                fields[field_name] = (python_type, Field(description=description))
            else:
                fields[field_name] = (Optional[python_type], Field(default=None, description=description))

    # Create the Pydantic model dynamically
    return create_model(model_name, **fields)


# Map JSON schema types to Python types
TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}
