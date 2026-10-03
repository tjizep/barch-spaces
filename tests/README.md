# Tests

The suite starts a temporary `barchd`, loads the viewer's function sources from
this checkout with `SETF`, and drives them over HTTP and RESP. Each test keeps its
own key spaces and its own port, so the suite can run beside a development server.

`test_spaces_viewer.py` starts HTTP for the `spaces` space and runs the viewer end
to end: registration, the first account becoming admin, the session cookie, the
admin and non-admin API split, key and function writes, space creation, sign-on,
and sign-out.

`test_stress.py` is opt-in (`BARCH_STRESS=1`): it creates thousands of sign-on
sessions under CPU pressure and checks the server stays up.

`conftest.py` and `helpers.py` are the harness from barchex, where the viewer came
from; some of their helpers serve barchex's other tests.

## Running

Install `pytest` and `redis` for Python, then:

```sh
BARCHD=/path/to/barchd pytest -q tests
```

Without `BARCHD`, the harness looks for `barchd` on `PATH`, then in a `barch`
checkout beside this one.
