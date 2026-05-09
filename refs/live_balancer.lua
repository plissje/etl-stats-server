-- live_balancer.lua (v4.1 - Smart Tag Enforcement)
et.RegisterModname("Live Balancer API")

local RENAME_DELAY    = 150   -- ms between rename queue items
local _rename_queue   = {}
local _rename_timer   = 0
local _tags           = {}    -- slot -> required tag (plain text)
local _official_names = {}    -- slot -> fallback full name

function sanitize_name(text)
    if not text then return "" end
    local s = string.gsub(text, "%^.", "") -- Strip ALL color codes
    s = string.gsub(s, "|", " ")
    s = string.gsub(s, ";", " ")
    s = string.gsub(s, '"', "'")
    s = string.gsub(s, ",", " ")
    return string.strip(s) or s
end

if not string.strip then
    function string.strip(s) return s:match("^%s*(.-)%s*$") end
end

local function execute_rename(slot, new_name)
    local info = et.trap_GetUserinfo(slot)
    if not info or info == "" then return end
    info = et.Info_SetValueForKey(info, "name", new_name)
    et.trap_SetUserinfo(slot, info)
    et.ClientUserinfoChanged(slot)
end

function et_RunFrame(levelTime)
    if #_rename_queue > 0 and levelTime > _rename_timer then
        local item = table.remove(_rename_queue, 1)
        if et.gentity_get(item.slot, "pers.connected") == 2 then
            execute_rename(item.slot, item.name)
        end
        _rename_timer = levelTime + RENAME_DELAY
    end
end

function et_ClientUserinfoChanged(slot)
    local tag = _tags[slot]
    if tag then
        local current = et.Info_ValueForKey(et.trap_GetUserinfo(slot), "name")
        local clean_current = sanitize_name(current):lower()
        local clean_tag = sanitize_name(tag):lower()
        
        -- SMART CHECK: Only enforce the prefix. Allow custom colors/nicks after the tag.
        if string.sub(clean_current, 1, #clean_tag) ~= clean_tag then
            -- Tag was removed! Snap back to official name
            table.insert(_rename_queue, {slot = slot, name = _official_names[slot]})
        end
    end
end

function et_ConsoleCommand()
    local cmd = et.trap_Argv(0)
    local cmd_l = string.lower(cmd)

    if cmd_l == "api_set_tag" then
        local slot = tonumber(et.trap_Argv(1))
        local tag  = et.trap_Argv(2)
        local full = et.trap_Argv(3)
        if slot and tag and full then
            _tags[slot] = tag
            _official_names[slot] = full
            table.insert(_rename_queue, {slot = slot, name = full})
        end
        return 1
    elseif cmd_l == "api_clear_tags" then
        _tags = {}
        _official_names = {}
        print("API_TAGS_CLEARED")
        return 1
    elseif cmd_l == "api_live_players" then
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
        
        print("\nAPI_PLAYERS_SYNC_COMPLETE - v4.1 (Smart Tags)\n")
        return 1
    end
    return 0
end

print("[Live API] LOADED - version 4.1")
et.trap_SendConsoleCommand(et.EXEC_APPEND, "say Live Balancer API v4.1 (Smart Tags)\n")
