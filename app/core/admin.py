from typing import Dict, Any, List
from enum import Enum

class FieldType(str, Enum):
    STRING = "string"
    TEXT = "text"
    EMAIL = "email"
    PASSWORD = "password"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    FILE = "file"
    IMAGE = "image"
    RICH_TEXT = "rich_text"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    FOREIGN_KEY = "foreign_key"
    JSON = "json"
    ARRAY = "array"

class AdminModelRegister:
    _models: Dict[str, Any] = {}
    _route_metadata: Dict[str, Any] = {}

    @classmethod
    def _get_field_type(cls, column_type, field_name: str) -> Dict[str, Any]:
        """Determine detailed field type and validation rules"""
        type_str = str(column_type).lower()
        
        field_info = {
            "type": None,
            "validation_rules": {},
            "ui_widget": None,
            "options": None
        }

        # Map SQL types to field types
        if "varchar" in type_str or "character varying" in type_str:
            # Try to get max_length from type string
            try:
                if "(" in type_str and ")" in type_str:
                    max_length = int(type_str.split("(")[1].split(")")[0])
                else:
                    max_length = 255  # Default length
                field_info["validation_rules"]["max_length"] = max_length
            except (IndexError, ValueError):
                field_info["validation_rules"]["max_length"] = 255

            if field_name in ["email", "email_address"]:
                field_info["type"] = FieldType.EMAIL
                field_info["validation_rules"]["pattern"] = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
            elif "password" in field_name:
                field_info["type"] = FieldType.PASSWORD
                field_info["validation_rules"]["min_length"] = 8
            else:
                field_info["type"] = FieldType.STRING
        
        elif "text" in type_str:
            if any(x in field_name for x in ["content", "description", "body"]):
                field_info["type"] = FieldType.RICH_TEXT
                field_info["ui_widget"] = "rich_text_editor"
            else:
                field_info["type"] = FieldType.TEXT
        
        elif "int" in type_str or "integer" in type_str:
            field_info["type"] = FieldType.INTEGER
            field_info["validation_rules"].update({
                "min": None,
                "max": None
            })
        
        elif "float" in type_str or "decimal" in type_str or "numeric" in type_str:
            field_info["type"] = FieldType.FLOAT
            field_info["validation_rules"]["precision"] = 2
        
        elif "bool" in type_str:
            field_info["type"] = FieldType.BOOLEAN
            field_info["ui_widget"] = "switch"
        
        elif "date" in type_str:
            if "timestamp" in type_str or "datetime" in type_str:
                field_info["type"] = FieldType.DATETIME
            else:
                field_info["type"] = FieldType.DATE
        
        elif "json" in type_str or "jsonb" in type_str:
            field_info["type"] = FieldType.JSON
            field_info["ui_widget"] = "json_editor"
        
        elif "array" in type_str:
            field_info["type"] = FieldType.ARRAY
            field_info["ui_widget"] = "multi_select"

        # Handle file and image fields based on field name
        if any(x in field_name for x in ["file", "attachment", "document"]):
            field_info["type"] = FieldType.FILE
            field_info["validation_rules"].update({
                "allowed_types": ["pdf", "doc", "docx"],
                "max_size": 5 * 1024 * 1024  # 5MB
            })
        
        elif any(x in field_name for x in ["image", "photo", "picture", "avatar"]):
            field_info["type"] = FieldType.IMAGE
            field_info["validation_rules"].update({
                "allowed_types": ["jpg", "jpeg", "png", "gif"],
                "max_size": 2 * 1024 * 1024,  # 2MB
                "dimensions": {
                    "max_width": 2000,
                    "max_height": 2000
                }
            })

        # Handle foreign keys
        if hasattr(column_type, "foreign_keys") and column_type.foreign_keys:
            field_info["type"] = FieldType.FOREIGN_KEY
            field_info["ui_widget"] = "select"
            # Get the reference table and column
            for fk in column_type.foreign_keys:
                field_info["foreign_key_details"] = {
                    "table": fk.column.table.name,
                    "column": fk.column.name
                }

        return field_info

    @classmethod
    def register(cls, model_class, **options):
        """Register a model with enhanced metadata"""
        model_name = model_class.__name__.lower()
        
        # Get relationships
        relationships = []
        for rel in model_class.__mapper__.relationships:
            relationships.append({
                "name": rel.key,
                "model": rel.mapper.class_.__name__.lower(),
                "type": "many" if rel.uselist else "one",
                "related_fields": [col.name for col in rel.local_columns],
                "display_fields": options.get(f"{rel.key}_display_fields", ["id", "name"])
            })

        # Get fields metadata
        fields = []
        for column in model_class.__table__.columns:
            field_type_info = cls._get_field_type(column.type, column.name)
            
            field = {
                "name": column.name,
                "type": field_type_info["type"],
                "nullable": column.nullable,
                "primary_key": column.primary_key,
                "foreign_key": bool(column.foreign_keys),
                "unique": column.unique,
                "default": str(column.default) if column.default else None,
                "validation_rules": field_type_info["validation_rules"],
                "ui_widget": field_type_info["ui_widget"],
                "options": field_type_info["options"],
                "help_text": options.get(f"{column.name}_help_text", ""),
                "label": options.get(f"{column.name}_label", column.name.replace("_", " ").title()),
                "placeholder": options.get(f"{column.name}_placeholder", "")
            }
            fields.append(field)

        cls._models[model_name] = {
            "model": model_class,
            "fields": fields,
            "relationships": relationships,
            "options": {
                "list_display": options.get("list_display", [field["name"] for field in fields]),
                "search_fields": options.get("search_fields", []),
                "filter_fields": options.get("filter_fields", []),
                "ordering": options.get("ordering", ["-id"]),
                "per_page": options.get("per_page", 10)
            }
        }

    @classmethod
    def get_metadata(cls) -> Dict:
        """Get metadata for all registered models"""
        return {
            "models": {
                name: {
                    "fields": info["fields"],
                    "relationships": info["relationships"],
                    "options": info["options"],
                    "endpoints": {
                        "list": f"/api/{name}s",
                        "detail": f"/api/{name}s/{{id}}",
                        "create": f"/api/{name}s",
                        "update": f"/api/{name}s/{{id}}",
                        "delete": f"/api/{name}s/{{id}}"
                    }
                }
                for name, info in cls._models.items()
            }
        }
    
    @classmethod
    def get_registered_models(cls) -> List:
        """Get a list of all registered model classes"""
        return [info["model"] for info in cls._models.values()]