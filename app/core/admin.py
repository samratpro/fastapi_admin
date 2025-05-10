from typing import Dict, Any, List
from fastapi import HTTPException

class AdminModelRegister:
    _models: Dict[str, Any] = {}

    @classmethod
    def register(cls, model_class, **options):
        """Register a model for admin interface"""
        model_name = model_class.__name__.lower()
        
        # Get relationships
        relationships = []
        for rel in model_class.__mapper__.relationships:
            relationships.append({
                "name": rel.key,
                "model": rel.mapper.class_.__name__.lower(),
                "type": "many" if rel.uselist else "one"
            })

        # Get fields metadata
        fields = []
        for column in model_class.__table__.columns:
            field = {
                "name": column.name,
                "type": str(column.type),
                "nullable": column.nullable,
                "primary_key": column.primary_key,
                "foreign_key": bool(column.foreign_keys),
                "unique": column.unique,
                "default": str(column.default) if column.default else None
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