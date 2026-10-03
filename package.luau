-- How barch-spaces installs itself from git:
--
--     barchd -g https://github.com/tjizep/barch-spaces user=default
--
-- Beside an app, give barchd both: -g <the app> -g <this>. barch applies this on
-- every sync, in this order: the space, the folder, the HTTP server, then the
-- after hook.
function setup()
    return {
        -- listed so the space exists after a sync, and is open after a restart
        -- before anything else touches it
        spaces = {
            spaces = {},
        },
        load = {
            { path = "spaces", space = "spaces" },
        },
        -- the viewer, at http://127.0.0.1:18091/spaces. SPACESAPI is an admin
        -- surface, so keep it on loopback
        http = { space = "spaces", key = "SPACESHTTP", port = 18091, bind = "127.0.0.1" },
        -- web's grants for the viewer. Hooks run as the repository's `user`,
        -- which whoever runs barchd picks; with no user this is skipped
        hooks = {
            after = { space = "spaces", call = "VIEWERGRANTS" },
        },
    }
end
