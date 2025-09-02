import random
import string
import uuid
from datetime import datetime, date
from enum import Enum
from typing import List, Optional, get_origin, get_args, Type, Union, Any, Annotated
from pydantic import BaseModel

class PydanticFactory:
    @staticmethod
    def generate_random_instance(model_cls: Type[BaseModel]) -> BaseModel:
        
        field_values = {}
        for field_name, field_info in model_cls.model_fields.items():
            field_type = field_info.annotation
            field_values[field_name] = PydanticFactory._generate_random_value(field_type, field_name)

        return model_cls(**field_values)

    @staticmethod
    def _generate_random_value(field_type: Any, field_name: str = ""):
        """
        Recursively generate a realistic random value based on the type annotation.
        Special handling for 'uuid' fields.
        """

        origin = get_origin(field_type)
        args = get_args(field_type)

        # Handle Optionals (Optional[T] is actually Union[T, None])
        if origin is Union and type(None) in args:
            actual_type = next(arg for arg in args if arg is not type(None))
            return PydanticFactory._generate_random_value(actual_type, field_name) if random.choice([True, False]) else None
        
        # Handle tuples
        if origin is tuple:
            if len(args) == 0:
                # No type hints inside, fallback to a generic tuple
                return tuple(random.randint(0, 100) for _ in range(3))
            else: 
                # Tuple has specific types like Tuple[float, float, float]
                return tuple(PydanticFactory._generate_random_value(arg) for arg in args)
                
        # Handle Lists (List[T] or typing.List[T])
        if origin in (list, List):
            inner_type = args[0]
            return [PydanticFactory._generate_random_value(inner_type) for _ in range(random.randint(1, 3))]
            
        # Handle Annotated types
        if origin is Annotated:
            core_type, constraints = PydanticFactory.extract_annotated_details(field_type)
            return PydanticFactory._generate_random_value_with_constraints(core_type, constraints)
            
        # Handle Enums
        if PydanticFactory._is_enum_type(field_type):
            return random.choice(list(field_type))

        # Handle Nested Pydantic Models
        if PydanticFactory._is_base_model_type(field_type):
            return PydanticFactory.generate_random_instance(field_type)

        # Handle UUIDs — if the field name contains 'uuid', 'id', or 'reference'
        if field_type is uuid.UUID:
            return uuid.uuid4()

        # Handle Primitive Types
        if field_type is str:
            return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        if field_type is int:
            return random.randint(1, 100)

        if field_type is float:
            return round(random.uniform(0.1, 100.0), 2)

        if field_type is bool:
            return random.choice([True, False])

        if field_type is datetime:
            return datetime.utcnow()

        if field_type is date:
            return datetime.utcnow().date()

        raise TypeError(f"Unhandled field type: {field_type}")
    
    @staticmethod
    def _generate_random_value_with_constraints(core_type: Any, constraints: dict):
        if get_origin(core_type) is list:
            inner_type = get_args(core_type)[0]
            return PydanticFactory.generate_annotated_list(inner_type, constraints)
        raise TypeError(f"Unsupported core type in Annotated: {core_type}")

    @staticmethod
    def _is_enum_type(typ: Any) -> bool:
        """
        Safe check if a type is an Enum.
        """
        try:
            return isinstance(typ, type) and issubclass(typ, Enum)
        except TypeError:
            return False

    @staticmethod
    def _is_base_model_type(typ: Any) -> bool:
        """
        Safe check if a type is a Pydantic BaseModel.
        """
        try:
            return isinstance(typ, type) and issubclass(typ, BaseModel)
        except TypeError:
            return False
            
    @staticmethod
    def extract_annotated_details(field_type: Any):
        """
        Extracts core type and constraints from an Annotated type.
        """
        if get_origin(field_type) is Annotated:
            core_type = get_args(field_type)[0]
            metadata = get_args(field_type)[1:]
            constraints = {}
            for meta in metadata:
                if hasattr(meta, 'min_length'):
                    constraints['min_length'] = meta.min_length
                if hasattr(meta, 'max_length'):
                    constraints['max_length'] = meta.max_length
            return core_type, constraints
        else:
            return field_type, {}

    @staticmethod
    def generate_annotated_list(inner_type: Any, constraints: dict):
        min_length = constraints.get('min_length', 1)
        max_length = constraints.get('max_length', 5)
        length = random.randint(min_length, max_length)

        if inner_type is int:
            return [random.randint(0, 100) for _ in range(length)]
        elif inner_type is float:
            return [round(random.uniform(0, 100), 2) for _ in range(length)]
        elif inner_type is str:
            return [''.join(random.choices('abcdefg', k=5)) for _ in range(length)]
        elif inner_type is bool:
            return [random.choice([True, False]) for _ in range(length)]
        elif PydanticFactory._is_base_model_type(inner_type):
            return [PydanticFactory.generate_random_instance(inner_type) for _ in range(length)]
        else:
            raise TypeError(f"Unhandled list inner type: {inner_type}")