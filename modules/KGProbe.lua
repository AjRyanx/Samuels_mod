-- KGProbe.lua  READ-ONLY probe (UNTESTED). Writes kgprobe.log in the sider folder.
-- Load it LAST in sider.ini. Press F9 to cycle the mode label: ML -> BAL -> EXH -> CUSTOM(ML w/ Mod Studio club).
local m = {}
local DIR, LABELS, li, seen, count = '', { 'ML', 'BAL', 'EXH', 'CUSTOM_ML' }, 0, {}, 0

local function W(s)
  local f = io.open(DIR .. 'kgprobe.log', 'a')
  if f then f:write(os.date('%H:%M:%S') .. ' ' .. s .. '\n'); f:close() end
end
local function label() return li == 0 and 'UNLABELLED' or LABELS[li] end

function m.key_down(ctx, vk)
  if vk == 0x78 then li = (li % #LABELS) + 1; seen = {}; count = 0; W('LABEL ' .. label()) end
end

function m.make_key(ctx, filename)
  local fn = tostring(filename)
  local kit = fn:find('uniform', 1, true) or fn:find('kit', 1, true) or fn:find('.ftex', 1, true)
  if kit then
    if not seen[fn] then seen[fn] = 0 end
    seen[fn] = seen[fn] + 1
    W('KITFILE [' .. label() .. '] ' .. fn .. ' (request #' .. seen[fn] .. ')')
  else
    count = count + 1
  end
  return nil
end

function m.set_teams(ctx, home, away)
  W('SET_TEAMS [' .. label() .. '] tournament_id=' .. tostring(ctx.tournament_id)
    .. ' competition_id=' .. tostring(ctx.competition_id)
    .. ' home=' .. tostring(home) .. ' away=' .. tostring(away)
    .. ' matchday=' .. tostring(ctx.matchday)
    .. ' year=' .. tostring(ctx.year) .. ' month=' .. tostring(ctx.month) .. ' day=' .. tostring(ctx.day)
    .. ' date=' .. tostring(ctx.date) .. ' time=' .. tostring(ctx.time)
    .. ' other_file_requests=' .. count)
  count = 0
end

function m.set_kits(ctx, home, away)
  W('SET_KITS [' .. label() .. '] home=' .. tostring(home) .. ' away=' .. tostring(away))
end

function m.context_reset(ctx) W('CONTEXT_RESET [' .. label() .. ']'); seen = {} end

function m.init(ctx)
  DIR = tostring(ctx.sider_dir or '')
  if DIR ~= '' and DIR:sub(-1) ~= '\\' and DIR:sub(-1) ~= '/' then DIR = DIR .. '/' end
  W('PROBE START sider_dir=' .. DIR)
  W('SANDBOX type(pcall)=' .. type(pcall) .. ' type(require)=' .. type(require) .. ' type(os.execute)=' .. type(os.execute)
    .. ' type(io.open)=' .. type(io.open) .. ' type(ffi)=' .. type(ffi) .. ' type(next)=' .. type(next) .. ' type(select)=' .. type(select))
  ctx.register('key_down', m.key_down)
  ctx.register('livecpk_make_key', m.make_key)
  ctx.register('set_teams', m.set_teams)
  ctx.register('set_kits', m.set_kits)
  ctx.register('context_reset', m.context_reset)
end
return m
