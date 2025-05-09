from typing import Dict, Any, List
from fastapi import HTTPException

class AdminModelRegister:
    _models: Dict[str, Any] = {}

    @classmethod
    def register(cls, model_class, **options):
        model_name = model_class.__name__.lower()
        cls._models[model_name] = {
            "model": model_class,
            "fields": cls.get_model_fields(model_class),
            "options": options
        }

    @classmethod
    def get_model_fields(cls, model_class) -> List[Dict]:
        fields = []
        for column in model_class.__table__.columns:
            field = {
                "name": column.name,
                "type": str(column.type),
                "nullable": column.nullable,
                "primary_key": column.primary_key,
                "unique": column.unique,
            }
            fields.append(field)
        return fields

    @classmethod
    def get_metadata(cls) -> Dict:
        return {
            name: {
                "fields": info["fields"],
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
