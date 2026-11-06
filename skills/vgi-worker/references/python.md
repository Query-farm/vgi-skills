# Python

Python 3.13+. Install the distribution `vgi-python==0.49.0`, import `vgi`. A standalone script can carry PEP 723 inline dependencies for `uv run`. A project can use `uv add vgi-python==0.49.0` and commit its lockfile.

```python
from typing import Annotated
import pyarrow as pa
import pyarrow.compute as pc
from vgi import Param, Returns, ScalarFunction, Worker
from vgi.catalog import Catalog, Schema

class Double(ScalarFunction):
    @classmethod
    def compute(cls, value: Annotated[pa.Int64Array, Param()]) -> Annotated[pa.Int64Array, Returns()]:
        return pc.multiply_checked(value, 2)

class Demo(Worker):
    catalog = Catalog(name="demo", schemas=[Schema(path=["main"], functions=[Double])])

if __name__ == "__main__":
    Demo().run()
```

Current releases use `Schema(path=["main"])` and client `schema_path=["main"]`. Older website examples use `name` / `schema_name`. Follow the selected release.

For table functions and catalogs, read the tagged example and exact installed signatures:
- https://github.com/Query-farm/vgi-python/blob/v0.49.0/examples/calc_worker.py
- https://query.farm/vgi/docs/python/
- Registry: https://pypi.org/project/vgi-python/0.49.0/

Do not use unbounded per-row network calls in `compute`. For external libraries, lock their versions and test their null/error behavior. Keep application logs on stderr.
