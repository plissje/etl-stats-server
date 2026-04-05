-- live_balancer.lua (v3.2 - 10-Chunk Compact Method)
et.RegisterModname("Live Balancer API")

function sanitize_name(text)
    if not text then return "" end
    local s = string.gsub(text, "%^.", "") -- Strip ALL color codes (^1, ^s, etc.)
    s = string.gsub(s, "|", " ")            -- Strip delims
    s = string.gsub(s, ";", " ")            -- Strip delims
    s = string.gsub(s, '"', "'")            -- Replace double quotes with single
    s = string.gsub(s, ",", " ")            -- Strip commas
    return string.strip(s) or s
end

-- Polyfill for older Lua versions if needed
if not string.strip then
    function string.strip(s)
        return s:match("^%s*(.-)%s*$")
    end
end

function et_ConsoleCommand()
    local cmd = et.trap_Argv(0)
    if string.lower(cmd) == "api_live_players" then
        local players = {}
        local maxclients = tonumber(et.trap_Cvar_Get("sv_maxclients")) or 64
        
        -- Reset all 10 CVARs first to avoid stale data from previous calls
        for i=1, 10 do
            et.trap_Cvar_Set("etl_live_api_" .. i, "")
        end

        for i=0, maxclients-1 do
            local team = tonumber(et.gentity_get(i, "sess.sessionTeam"))
            -- Include Axis (1), Allies (2), and Spectator (3)
            if team and (team >= 1 and team <= 3) then
                local userinfo = et.trap_GetUserinfo(i)
                if userinfo ~= "" then
                    local name = et.gentity_get(i, "pers.netname")
                    if not name or name == "" or name == "default:" then
                        name = et.Info_ValueForKey(userinfo, "name")
                    end
                    local guid = et.Info_ValueForKey(userinfo, "cl_guid")
                    if not guid or guid == "" then
                        guid = et.Info_ValueForKey(userinfo, "guid")
                    end
                    
                    if name and name ~= "" and guid and guid ~= "" then
                        local clean_name = sanitize_name(name)
                        -- Format: slot|guid|team|name
                        table.insert(players, string.format('%d|%s|%d|%s', i, guid, team, clean_name))
                    end
                end
            end
        end
        
        -- CHUNKING: Split into 10 chunks of 4 players each (40 total)
        -- Smaller chunks are much safer for CVAR string limits (usually < 1024)
        local players_per_chunk = 4
        for chunk_idx = 1, 10 do
            local chunk_data = {}
            local start_idx = (chunk_idx - 1) * players_per_chunk + 1
            local end_idx = chunk_idx * players_per_chunk
            
            for p_idx = start_idx, end_idx do
                if players[p_idx] then
                    table.insert(chunk_data, players[p_idx])
                end
            end
            
            if #chunk_data > 0 then
                et.trap_Cvar_Set("etl_live_api_" .. chunk_idx, table.concat(chunk_data, ";"))
            end
        end
        
        print("\nAPI_PLAYERS_SYNC_COMPLETE - v3.2 (10 Chunks)\n")
        return 1
    end
    return 0
end

print("[Live API] LOADED - version 3.2")
et.trap_SendConsoleCommand(et.EXEC_APPEND, "say Live Balancer API v3.2\n")
