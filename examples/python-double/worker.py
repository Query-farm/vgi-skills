# /// script
# requires-python = ">=3.13"
# dependencies = ["vgi-python==0.49.0"]
# ///
"""Small verification fixture; use the skill to build your own capability."""
from typing import Annotated
import pyarrow as pa
import pyarrow.compute as pc
from vgi import Param, Returns, ScalarFunction, Worker
from vgi.catalog import Catalog, Schema


class Double(ScalarFunction):
    """Double signed integers, preserving nulls."""

    @classmethod
    def compute(cls, value: Annotated[pa.Int64Array, Param()]) -> Annotated[pa.Int64Array, Returns()]:
        return pc.multiply_checked(value, 2)


class Demo(Worker):
    catalog = Catalog(name="demo", schemas=[Schema(path=["main"], functions=[Double])])


if __name__ == "__main__":
    Demo().run()
