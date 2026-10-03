# barch-spaces

A web page for looking inside a barch server: every key space, its keys and
values, its file store, its functions, and its settings. Admins can also edit keys
and files, write and run functions, create spaces, change settings, import and
export, and run any command from a console. It used to live in
[barchex](https://github.com/tjizep/barchex); it has its own repository now, so it
can sit beside any app.

## Install with barchd -g

```
barchd --port 14000 --dir data -g https://github.com/tjizep/barch-spaces user=default
```

`package.luau` creates the `spaces` key space, loads the `spaces/` folder into it,
and starts the viewer at `http://127.0.0.1:18091/spaces`. It comes back after a
restart. Keep it on loopback: `SPACESAPI` can export, import and change settings.

To look inside an app, give barchd the app and this, each with its own `-g`. For
[the shop](https://github.com/tjizep/barch-shop):

```
barchd --port 14000 --dir data \
  -g https://github.com/tjizep/barch-shop user=default \
  -g https://github.com/tjizep/barch-spaces user=default
```

The shop stays at `http://127.0.0.1:18090/shop`, and the viewer is at
`http://127.0.0.1:18091/spaces`.

The viewer's routes run as the `web` user. The package's after hook,
`VIEWERGRANTS`, adds the categories the viewer needs to `web`'s rule: `read`,
`write`, `data`, `keys`, `function`, `config` and `dangerous`. A category that
`web`'s rule already sets, either way, stays as it is. The hook runs as the
repository's `user`; without `user=`, barchd skips it, and you grant `web` its
rights yourself with the `ACL SETUSER` line further down. `web` is also the user an
app's routes usually run as, the shop's included, so installing the viewer beside
an app gives that app's routes these rights too.

## What it contains

```
package.luau        →  how barchd -g installs this repository
spaces/
  spacesapi.luau    →  function SPACESAPI    (GET/POST /api/admin/*)
  spacesui.luau     →  function SPACESUI     (GET /spaces)
  users.luau        →  function USERS        (accounts in this space)
  spaceshttp.luau   →  function SPACESHTTP   (the viewer's HTTP server)
  viewergrants.luau →  function VIEWERGRANTS (package.luau's after hook)
  spaces.html       →  key spaces.html
  commands.json     →  key commands.json     (the console's command list)
tests/              →  not loaded; see Tests below
```

## Using the viewer

USERS keeps `user:`, `sess:` and `admin:` keys in `spaces`, not in a `users` key
space. On a server with no admin yet, the page asks you to make an account, and the
first account made, or the first existing account to sign on, becomes the admin.
Until then there is no way in, so do that first.

The gear beside a space's name opens its settings. The function limits
(`function_deadline_ms`, `function_deadline_max_ms`, `function_slice_insns`
and `function_slice_max_insns`) each have a dropdown, and the page shows the
value the space runs with now. A change is saved as `<space>.<setting>` in the
`configuration` space and takes effect the next time the space loads, which
means after a server restart. Long calls from the viewer run inside
`SPACESAPI` in the `spaces` space, so raise the deadline of `spaces` when Call
reports `FUNCTION timeout`.

**New space** asks for a name, the function deadline and the function slice.
Open **Advanced** to choose how the space stores its keys. The viewer writes
each choice as `<space>.<setting>` in the `configuration` space before it
creates the space, so the space loads with them. A field left on its server
default writes nothing, and the space keeps following the server.

| Field | Setting | Values |
|---|---|---|
| Shards | `shards` | A whole number from 1 to 256. Server default `internal_shards`. |
| Key order | `ordered` | `1` ordered, `0` unordered. |
| Key routing | `range_sharded` | `Range` writes `1`. `Hash` writes nothing. Range needs ordered keys, so the choice is disabled while the space is unordered. |
| Hybrid keys | `hybrid` | `1` on, `0` off. |
| Compression | `compression` | `zstd` or `off`. |
| Key split | `key_split` | A regular expression. The viewer rejects one that does not compile. |
| Change log | `aof` | `on` writes to the server's `aof_dir`. The field is disabled while `aof_dir` is `off`. |

A space cannot change its shard count, key order or routing once it holds data,
so set them here. The viewer lists the keys of an ordered space only. Settings
that need outside resources, such as a foreign source, a file source or arena
paths, are keys in the `configuration` space that you edit directly before the
space is first used.

**Add a service…** in the Code view opens a new function with a `service()`
template for an HTTP route, an HTTP server, an HTTP starter, static files,
RESP commands, a queue consumer or a cron job. The comments in each template
say where it is stored and how to start it; queue and cron templates open in
`configuration`. The HTTP starter runs `HTTP START` for the space when you
press Call, and a cron job can call it every minute to bring the server back
after a restart.

In the Files view, text files open in an editor with **Save**, and `.luau`
files get the Luau editor and a **Run** box. A `.luau` file is a module that
a stored function loads with `require(":/path/file.luau")`; Run does that
through `RUNLUAU`, a small function it stores in the space the first time,
and calls the file's `call()` with the arguments. The file is read fresh on
each run, and errors point at the file's own lines. The gear beside Save sets
**Native**, **Deadline** and **Slice** as header lines in the file. barch
compiles a required file natively when it has `--!native`, but takes a call's
deadline and slice from the function that is called, so Run copies the file's
`--@barch` line onto `RUNLUAU` before it calls it. A function that requires
the file runs with its own limits.

The function editor and the `.luau` file editor have a prompt bar for asking
a model about the code or for describing a change. Paste an OpenRouter API key into the bar, or into
App settings, to turn it on. The browser sends the question straight to
`openrouter.ai`, together with the context ticked under the bar: the source
in the editor, the last Call output, and the first 20 keys of the space with
a short preview of each. Leave the key sample unticked when the space holds
data that should stay on the server. The key is stored in the browser's
`localStorage`, and barch never receives it. Choose the model in App settings;
the default is the newest Claude Sonnet that OpenRouter lists. **Apply to
editor** replaces the editor's content with the answer's code block. The
stored function changes when you press Save, or Call while Save before Call
is on (the default).

## Install with FUNCTIONS SYNC

To add the viewer to a server that is already running, configure the repository
in the `configuration` space and sync it:

```
USE configuration
SET git/repositories/barch-spaces/url    https://github.com/tjizep/barch-spaces
SET git/repositories/barch-spaces/pull   on
SET git/repositories/barch-spaces/user   default   # runs VIEWERGRANTS; omit to grant web yourself

FUNCTIONS SYNC barch-spaces
FUNCTIONS STATUS
```

The sync applies `package.luau` the same way `barchd -g` does. Leave the
repository's `as` on `keys` and `space` off; barch refuses a package that lists
folders while either is set to something else.

To start the viewer by hand, for example on another port, run
`HTTP START SPACESHTTP <port> 127.0.0.1` in the `spaces` space. The HTTP user
needs the rights the page's buttons ask for. `+dangerous` lets Import and Export
through (`IMPORT` carries the `dangerous` category; `EXPORT` does not).
`ACL SETUSER` adds the categories it names to the user's rule and leaves the
others as they are.

```
ACL SETUSER web on +read +write +data +keys +function +config +dangerous
```

`+admin` is not a grantable right: `admin` is a preset name, so a `SETUSER` that
includes it fails with `ACL category not found`.

## Tests

`tests/` starts a temporary `barchd`, loads the viewer's functions from this
checkout with `SETF`, starts HTTP for the `spaces` space, and runs the viewer end
to end: registration, the first account becoming admin, the session cookie, the
admin and non-admin API split, key and function writes, space creation, sign-on,
and sign-out. Install `pytest` and `redis` for Python, then:

```sh
BARCHD=/path/to/barchd pytest -q tests
```
