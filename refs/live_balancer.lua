-- live_balancer.lua (v2.0 - Chunked Compact Method)
et.RegisterModname("Live Balancer API")

function strip_colors(text)
    if not text then return "" end
    return string.gsub(text, "%^%d", "")
end

function et_ConsoleCommand()
    local cmd = et.trap_Argv(0)
    if string.lower(cmd) == "api_live_players" then
        local players = {}
        local maxclients = tonumber(et.trap_Cvar_Get("sv_maxclients")) or 64
        
        for i=0, maxclients-1 do
            local team = tonumber(et.gentity_get(i, "sess.sessionTeam"))
            if team and (team >= 1 and team <= 3) then
                local userinfo = et.trap_GetUserinfo(i)
                if userinfo ~= "" then
                    local name = et.Info_ValueForKey(userinfo, "name")
                    local guid = et.Info_ValueForKey(userinfo, "cl_guid")
                    if not guid or guid == "" then
                        guid = et.Info_ValueForKey(userinfo, "guid")
                    end
                    
                    if name and name ~= "" and guid and guid ~= "" then
                        -- COMPACT FORMAT: s|g|t|n;
                        local clean_name = strip_colors(name)
                        -- Replace delimiters to avoid formatting breakage
                        clean_name = string.gsub(clean_name, "|", " ")
                        clean_name = string.gsub(clean_name, ";", " ")
                        
                        table.insert(players, string.format('%d|%s|%d|%s', i, guid, team, clean_name))
                    end
                end
            end
        end
        
        -- CHUNKING: Split into 2 chunks of 15 players each (30 total)
        local chunk1 = {}
        local chunk2 = {}
        for idx, p in ipairs(players) do
            if idx <= 15 then
                table.insert(chunk1, p)
            else
                table.insert(chunk2, p)
            end
        end
        
        et.trap_Cvar_Set("etl_live_api_1", table.concat(chunk1, ";"))
        et.trap_Cvar_Set("etl_live_api_2", table.concat(chunk2, ";"))
        
        print("\nAPI_PLAYERS_SYNC_COMPLETE - v2.0\n")
        return 1
    end
    return 0
end

print("[Live API] LOADED - version 2.0 (Chunked Compact)")
et.trap_SendConsoleCommand(et.EXEC_APPEND, "say Live Balancer API v2.0 Loaded (Chunked)\n")
