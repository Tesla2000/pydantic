from dataclasses import InitVar
from typing import Any, ClassVar, Generic, Optional, TypeVar, Union

from typing_extensions import Self

from pydantic import BaseModel, ConfigDict, Field, RootModel, create_model, field_validator, model_validator, validator
from pydantic.dataclasses import dataclass


class Model(BaseModel):
    x: float
    y: str

    model_config = ConfigDict(from_attributes=True)


class SelfReferencingModel(BaseModel):
    submodel: Optional['SelfReferencingModel']

    @property
    def prop(self) -> None:
        ...


SelfReferencingModel.model_rebuild()

model = Model(x=1, y='y')
Model(x=1, y='y', z='z')
# MYPY: error: Unexpected keyword argument "z" for "Model"  [call-arg]
model.x = 2
model.model_validate(model)

self_referencing_model = SelfReferencingModel(submodel=SelfReferencingModel(submodel=None))


class KwargsModel(BaseModel, from_attributes=True):
    x: float
    y: str


kwargs_model = KwargsModel(x=1, y='y')
KwargsModel(x=1, y='y', z='z')
# MYPY: error: Unexpected keyword argument "z" for "KwargsModel"  [call-arg]
kwargs_model.x = 2
kwargs_model.model_validate(kwargs_model.__dict__)


class InheritingModel(Model):
    z: int = 1


InheritingModel.model_validate(model.__dict__)


class ForwardReferencingModel(Model):
    future: 'FutureModel'


class FutureModel(Model):
    pass


ForwardReferencingModel.model_rebuild()
future_model = FutureModel(x=1, y='a')
forward_model = ForwardReferencingModel(x=1, y='a', future=future_model)


class NoMutationModel(BaseModel):
    x: int

    model_config = ConfigDict(frozen=True)


class MutationModel(NoMutationModel):
    a: int = 1

    model_config = ConfigDict(frozen=False, from_attributes=True)


MutationModel(x=1).x = 2
MutationModel.model_validate(model.__dict__)


class KwargsNoMutationModel(BaseModel, frozen=True):
    x: int


class KwargsMutationModel(KwargsNoMutationModel, frozen=False, from_attributes=True):
# MYPY: error: Non-frozen dataclass cannot inherit from a frozen dataclass  [misc]
    a: int = 1


KwargsMutationModel(x=1).x = 2
# MYPY: error: Property "x" defined in "KwargsNoMutationModel" is read-only  [misc]
KwargsMutationModel.model_validate(model.__dict__)


class OverrideModel(Model):
    x: int


OverrideModel(x=1, y='b')


class Mixin:
    def f(self) -> None:
        pass


class MultiInheritanceModel(BaseModel, Mixin):
    pass


MultiInheritanceModel().f()


class AliasModel(BaseModel):
    x: str = Field(alias='x_alias')
    y: str = Field(validation_alias='y_alias')
    z: str = Field(validation_alias='z_alias', alias='unused')


alias_model = AliasModel(x_alias='a', y_alias='a', z_alias='a')
# MYPY: error: Unexpected keyword argument "y_alias" for "AliasModel"; did you mean "x_alias"?  [call-arg]
# MYPY: error: Unexpected keyword argument "z_alias" for "AliasModel"; did you mean "x_alias"?  [call-arg]
assert alias_model.x == 'a'
assert alias_model.y == 'a'
assert alias_model.z == 'a'


class ClassVarModel(BaseModel):
    x: int
    y: ClassVar[int] = 1


ClassVarModel(x=1)


@dataclass(config={'validate_assignment': True})
class AddProject:
    name: str
    slug: Optional[str]
    description: Optional[str]


p = AddProject(name='x', slug='y', description='z')


class TypeAliasAsAttribute(BaseModel):
    __type_alias_attribute__ = Union[str, bytes]


class NestedModel(BaseModel):
    class Model(BaseModel):
        id: str

    model: Model


_ = NestedModel.Model


DynamicModel = create_model('DynamicModel', __base__=Model)

dynamic_model = DynamicModel(x=1, y='y')
dynamic_model.x = 2


class FrozenModel(BaseModel):
    x: int

    model_config = ConfigDict(frozen=True)


class NotFrozenModel(FrozenModel):
    a: int = 1

    model_config = ConfigDict(frozen=False, from_attributes=True)


NotFrozenModel(x=1).x = 2
NotFrozenModel.model_validate(model.__dict__)


class KwargsFrozenModel(BaseModel, frozen=True):
    x: int


class KwargsNotFrozenModel(FrozenModel, frozen=False, from_attributes=True):
    a: int = 1


KwargsNotFrozenModel(x=1).x = 2
KwargsNotFrozenModel.model_validate(model.__dict__)


class ModelWithSelfField(BaseModel):
    self: str


def f(name: str) -> str:
    return name


class ModelWithAllowReuseValidator(BaseModel):
    name: str
    normalize_name = field_validator('name')(f)


model_with_allow_reuse_validator = ModelWithAllowReuseValidator(name='xyz')


T = TypeVar('T')


class Response(BaseModel, Generic[T]):
    data: T
    error: Optional[str]


response = Response[Model](data=model, error=None)


class ModelWithAnnotatedValidator(BaseModel):
    name: str

    @field_validator('name')
    def noop_validator_with_annotations(cls, name: str) -> str:
        return name


def _default_factory_str() -> str:
    return 'x'


def _default_factory_list() -> list[int]:
    return [1, 2, 3]


class FieldDefaultTestingModel(BaseModel):
    # Required
    a: int
    b: int = Field()
    c: int = Field(...)

    # Default
    d: int = Field(1)

    # Default factory
    g: list[int] = Field(default_factory=_default_factory_list)
    h: str = Field(default_factory=_default_factory_str)
    i: str = Field(default_factory=lambda: 'test')


_TModel = TypeVar('_TModel')
_TType = TypeVar('_TType')


class OrmMixin(Generic[_TModel, _TType]):
    @classmethod
    def from_orm(cls, model: _TModel) -> _TType:
        raise NotImplementedError

    @classmethod
    def from_orm_optional(cls, model: Optional[_TModel]) -> Optional[_TType]:
        if model is None:
            return None
        return cls.from_orm(model)


@dataclass
class MyDataClass:
    foo: InitVar[str]
    bar: str


MyDataClass(foo='foo', bar='bar')


def get_my_custom_validator(field_name: str) -> Any:
    @validator(field_name, allow_reuse=True)
    def my_custom_validator(cls: Any, v: int) -> int:
        return v

    return my_custom_validator


def foo() -> None:
    class MyModel(BaseModel):
        number: int
        custom_validator = get_my_custom_validator('number')  # type: ignore[pydantic-field]
# MYPY: error: Unused "type: ignore" comment  [unused-ignore]

        @model_validator(mode='before')
        @classmethod
        def validate_before(cls, values: Any) -> Any:
            return values

        @model_validator(mode='after')
        def validate_after(self) -> Self:
            return self

    MyModel(number=2)


class InnerModel(BaseModel):
    my_var: Union[str, None] = Field(default=None)


class OuterModel(InnerModel):
    pass


m = OuterModel()
if m.my_var is None:
    # In https://github.com/pydantic/pydantic/issues/7399, this was unreachable
    print('not unreachable')


class Foo(BaseModel):
    pass


class Bar(Foo, RootModel[int]):
    pass


class Model1(BaseModel):
    model_config = ConfigDict(validate_by_alias=False, validate_by_name=True)

    my_field: str = Field(alias='my_alias')

m1 = Model1(my_field='foo')
# MYPY: error: Unexpected keyword argument "my_field" for "Model1"  [call-arg]

class Model2(BaseModel):
    model_config = ConfigDict(validate_by_alias=True, validate_by_name=False)

    my_field: str = Field(alias='my_alias')

m2 = Model2(my_alias='foo')

class Model3(BaseModel):
    model_config = ConfigDict(validate_by_alias=True, validate_by_name=True)

    my_field: str = Field(alias='my_alias')

# for this case, we prefer the field name over the alias
m3 = Model3(my_field='foo')
# MYPY: error: Unexpected keyword argument "my_field" for "Model3"  [call-arg]

class Model4(BaseModel):
    my_field: str = Field(alias='my_alias')

m4 = Model4(my_alias='foo')

class Model5(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    my_field: str = Field(alias='my_alias')

m5 = Model5(my_field='foo')
# MYPY: error: Unexpected keyword argument "my_field" for "Model5"  [call-arg]
