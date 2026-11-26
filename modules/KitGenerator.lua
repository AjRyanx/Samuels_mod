-- KitGenerator.lua  (v0.8.0-beta.1)
-- SP Football Life 2027 sponsor / kit module.
--
--   * Sponsor Office (executive card UI) lists this season's offers for your
--     club (pre-season only) and shows the active deal as a dashboard card
--     with a financial summary and a contract progress bar.
--   * Signing a deal:  rebuilds the home/away/third kits (new design + the
--     sponsor logo) through the background watcher, and credits the deal's
--     yearly value (EUR, 50M-150M) into the in-game budgets, split between the
--     transfer budget and the salary budget (see TRANSFER_SHARE below).  Any
--     signing bonus on the offer is paid once, at signing.
--   * A multi-season deal blocks any new offers until it ends, but a fresh kit
--     is generated for every season it runs.  When it ends the contract is
--     released (offers reopen) and the logo comes off the kit.  You can also
--     terminate early: an early-exit clause pays TERMINATION_PCT of the value
--     still to run as a buyout and takes the logo off at once.
--   * Season lifecycle: Season 1 keeps every club on its authentic licensed
--     kit (the user club switches immediately if a deal is signed).  From
--     Season 2 all clubs use generated kits: p1/g1 (the "scoutable roster") are
--     built for every club at rollover, while p2/p3/g2 are built on demand for
--     scheduled opponents.  An expired deal leaves the user club sponsorless.
--   * Two independent halves (CFG.ENABLE_KITS / CFG.ENABLE_SPONSORSHIP): use the
--     kit half alone, the sponsorship half alone, or both together.
--   * v0.8 beta: the club you manage is AUTO-DETECTED.  Start a Master League with
--     any team and the mod follows it -- the club that turns up in every career
--     match wins, its kit colours are read live from the game
--     (ctx.kits.get) and written to content/KitGenerator/club.txt for the
--     Python generator, and offers are synthesised for that club when
--     deals.txt has none.  Set CFG.MANAGED_CLUB to a team id to override, or
--     type one in the Sponsor Office.
--
-- Written for Sider's LuaJIT sandbox: no pcall, require, select, next or print.
-- Uses the globals `ffi`, `memory` and `log`.
local m = { version = '0.8.0-beta.1' }

-- ===== config =============================================================
-- Two independent halves -- set either off to use the other on its own:
--   ENABLE_KITS        the kit half: rebuilds the club's home/away/third kits
--                      each season through the background Python watcher.
--   ENABLE_SPONSORSHIP the deal half: the Sponsor Office (offers, signing) and
--                      crediting the deal's money into the in-game budgets.
-- Both on = the full mod.  Kits only = fresh kits each season, no office and no
-- money.  Sponsorship only = the office and the money, but the kits are left
-- exactly as they are (no watcher, no Python needed).
local CFG = {
  ENABLE_KITS        = true,     -- rebuild the club's kits (needs the Python watcher)
  ENABLE_SPONSORSHIP = true,     -- Sponsor Office: offers, signing and budget money
  START_PROCESS      = true,     -- launch the kit watcher at game load (run setup_watcher.py once)
  OFFICE_KEY         = 0x78,     -- F9: classic text office (F7 is used by camera_dinamica)
  WINDOW_KEY         = 0x7A,     -- F11: manual transfer window toggle (F10 is used by camera_dinamica)
  SIGNING_MONTHS     = {6, 7, 8},-- PRE-SEASON only (Jun-Aug); Jan is deliberately excluded
  CREDIT_BUDGET      = true,     -- credit signed deals into the in-game budgets
  TERMINATION_PCT    = 0.50,     -- early-exit clause: pay this share of the value still to run
  MONEY_UNIT         = 100,      -- budgets are stored as a u32 in units of EUR 100
  MAX_BUDGET         = 4294967295, -- u32 ceiling (~EUR 429bn; the format's real limit)
  SALARY_DELTA       = 0x14,     -- salary budget sits this far past the transfer budget
  TRANSFER_SHARE     = 0.70,     -- share of each payment added to the transfer budget
  SALARY_SHARE       = 0.30,     -- ...and to the salary budget (must sum to 1.0)
  DYNAMIC_KIT_START_SEASON = 2028, -- Season 1 (2026/27) authentic; dynamic kits from Season 2 (2027/28)
  ROLLOVER_MODE      = "balanced", -- "balanced" (p1 + g1 Scoutable Roster, ~5-10 min, quiet) or "power" (all 5 slots upfront)
}
m.CFG = CFG

local STATE = { month = nil, year = nil,
                date_ok = false,
                -- managed-club auto-detection (see the club section below)
                club = nil, club_source = nil, club_name = nil,
                colors = {},        -- team id -> kit colours read from the game
                votes = {},         -- team id -> times seen in a career match
                matches = 0 }       -- career matches seen since the game loaded
local OFFICE = { open = false, sel = 1 }
local SEL = { counter = nil, ask = 1, reply = nil, credit_msg = nil, rounds = {}, term_confirm = false }
local OFFERS, SIGNED, BRANDS = {}, {}, {}
local OPTED_IN = {}
local DEAL = nil                      -- active multi-season deal (or nil)
local REQ_SEASONS, PAID, WARNED, CLEAN = {}, {}, {}, {}
local REQ_LEAGUE, JIT_REQUESTED = {}, {}
local CLEAN_PENDING = {}          -- club:season -> clean request id; blocks stale branded kits until the watcher finishes
local club_id, start_watcher, load_deal, reset_career_state

local DIR, CAREER, SEASON = '', 'unknown', 2027
local MONTH_NAMES = { 'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec' }

local function L(msg) log('[KitGenerator] ' .. tostring(msg)) end

-- ===== ffi (kernel32: WinExec / process id) ===============================
local ffi = ffi
local kernel32 = nil
if ffi then
  if not ffi.kg_declared then
    ffi.cdef([[
      unsigned int WinExec(const char* lpCmdLine, unsigned int uCmdShow);
      unsigned int GetCurrentProcessId(void);
    ]])
    ffi.kg_declared = true
  end
  kernel32 = ffi.load('kernel32')
end

local function get_pid()
  if kernel32 and kernel32.GetCurrentProcessId then
    return tonumber(kernel32.GetCurrentProcessId())
  end
  return nil
end

local function run_winexec(cmd)
  if kernel32 and kernel32.WinExec then
    return kernel32.WinExec(cmd, 0)
  end
  return nil
end

-- ===== small helpers ======================================================
-- All file paths go through here. Sider on Windows uses backslashes;
-- on Unix/macOS test environments forward slashes are preserved.
-- Sider's Lua sandbox does not expose the `package` global. Plain Lua (used by
-- the test suite) does, so prefer package.config there and default to Windows
-- inside Sider (the game runs on Windows).
local IS_WINDOWS = true
if package and package.config then
  IS_WINDOWS = (package.config:sub(1, 1) == '\\')
end
local function path(rel)
  local p = DIR .. 'content/KitGenerator/' .. rel
  return IS_WINDOWS and p:gsub('/', '\\') or p:gsub('\\', '/')
end

-- a path relative to SiderAddons itself (for files outside content/KitGenerator)
local function sider_path(rel)
  local p = DIR .. rel
  return IS_WINDOWS and p:gsub('/', '\\') or p:gsub('\\', '/')
end

-- ===== low-level memory helpers ===========================================
-- Sider can hand addresses back as cdata/userdata; normalise to a Lua number.
local function num_addr(x)
  if type(x) == 'number' then return x end
  if not x then return nil end
  if ffi and type(x) == 'cdata' then
    return tonumber(ffi.cast('uint64_t', x))
  end
  local direct = tonumber(x)
  if direct then return direct end
  if memory and memory.pack and memory.unpack then
    local packed = memory.pack('u64', x)
    if packed then return tonumber(memory.unpack('u64', packed)) end
  end
  if memory and memory.hex then
    local h = memory.hex(x)
    if h then return tonumber(h, 16) end
  end
  return nil
end

local function mread_u32(addr)
  local s = memory.read(addr, 4)
  if type(s) ~= 'string' or #s ~= 4 then return nil end
  return tonumber(memory.unpack('u32', s))
end

-- read a validated 64-bit pointer stored at `addr`
local function read_ptr_at(addr)
  local s = memory.read(addr, 8)
  if type(s) ~= 'string' or #s ~= 8 then return nil end
  local v = tonumber(memory.unpack('u64', s))
  if not v or v < 0x10000 or v >= 0x800000000000 then return nil end
  return v
end

local function split(line)
  local t = {}
  for f in (line .. '|'):gmatch('([^|]*)|') do t[#t + 1] = f end
  return t
end

-- djb2: the deterministic roll shared with kg_core.py (plain arithmetic, no bit ops)
local function hash(s)
  local h = 5381
  for i = 1, #s do h = (h * 33 + s:byte(i)) % 4294967296 end
  return h
end

-- hash -> [0,1), for the offer synthesis (same roll every reload and season)
local function hash01(s) return (hash(s) % 10000) / 10000 end

local function fmt_money(v)
  v = tonumber(v) or 0
  if v >= 1e9 then return string.format('EUR %.2fB', v / 1e9)
  elseif v >= 1e6 then return string.format('EUR %.1fM', v / 1e6)
  elseif v >= 1e3 then return string.format('EUR %.0fk', v / 1e3) end
  return 'EUR ' .. tostring(math.floor(v))
end

-- ---- executive office presentation helpers -------------------------------
-- sponsor tier -> the label shown on the deal card
local TIER_LABEL = { small = 'Tier 3  -  KIT SPONSOR',
                     mid   = 'Tier 2  -  MAIN KIT SPONSOR',
                     big   = 'Tier 1  -  MAIN KIT SPONSOR' }
local function tier_label(t)
  return TIER_LABEL[t] or 'KIT SPONSOR'
end

-- ASCII progress bar, e.g. [==========              ]  (font-safe: no unicode)
local function progress_bar(cur, total, width)
  width = width or 24
  cur = tonumber(cur) or 0
  total = tonumber(total) or 1
  if total < 1 then total = 1 end
  if cur < 0 then cur = 0 end
  if cur > total then cur = total end
  local filled = math.floor(width * cur / total + 0.5)
  if filled > width then filled = width end
  return '[' .. string.rep('=', filled) .. string.rep(' ', width - filled) .. ']'
end

local function plural(n, word)
  n = tonumber(n) or 0
  return tostring(n) .. ' ' .. word .. (n == 1 and '' or 's')
end

local function append_line(rel, text)
  local p = path(rel)
  local posix_p = (DIR .. 'content/KitGenerator/' .. rel)
  for attempt = 1, 8 do
    local f = io.open(p, 'a') or io.open(posix_p, 'a')
    if f then
      f:write(text .. '\n')
      f:flush()
      f:close()
      return true
    end
    local t0 = os.clock()
    while os.clock() - t0 < 0.015 do end
  end
  return false
end

local function write_file(rel, text)
  local p = path(rel)
  local posix_p = (DIR .. 'content/KitGenerator/' .. rel)
  for attempt = 1, 8 do
    local f = io.open(p, 'w') or io.open(posix_p, 'w')
    if f then
      f:write(text)
      f:flush()
      f:close()
      return true
    end
    local t0 = os.clock()
    while os.clock() - t0 < 0.015 do end
  end
  return false
end

local function read_lines(rel)
  local p = path(rel)
  local posix_p = (DIR .. 'content/KitGenerator/' .. rel)
  for attempt = 1, 8 do
    local out, f = {}, io.open(p, 'r') or io.open(posix_p, 'r')
    if f then
      for line in f:lines() do out[#out + 1] = line end
      f:close()
      return out
    end
    local t0 = os.clock()
    while os.clock() - t0 < 0.015 do end
  end
  return {}
end

local function in_signing_window()
  if CFG.ALLOW_OFF_SEASON then return true end
  if STATE.manual_window then return true end
  if not STATE.month then return true end
  for _, mm in ipairs(CFG.SIGNING_MONTHS) do
    if STATE.month == mm then return true end
  end
  return false
end

-- ===== game date (the Master League calendar) =============================
-- Sider's set_teams / make_key context carries NO date (only tournament_id:
-- confirmed with a probe), so the date is read straight out of the game.
-- The ML calendar sits in the edit context:
--   FL26 / FL27 modpack layout: offset 0x19115EC
--   Stock PES 2021 layout:      offset 0x1642A24
-- Bitfield layout:
--   bytes 0..1: year (u16 little-endian, e.g. 2026)
--   byte 2:     month (u8, 1..12)
--   byte 3:     day (u8, 1..31)
--   bytes 8..11: compact identity -> (team_id << 14) | team_array_slot
-- Decimal layout (fallback):
--   bytes 0..3: YYYYMMDD (u32 little-endian)
local DATE = { ready = false, global_ptr = nil, off = 0x19115EC, mode = nil }
local AOB_MODE = '\x48\x8B\x05\xA9\xF3\x24\x02\xC3'
local KNOWN_DATE_GETTER = 0x1414B6A60
local CAREER_OFFSETS = { 0x19115EC, 0x1642A24 }

local function install_date_reader()
  if DATE.ready then return true end
  if not (memory and memory.search_process and memory.read and memory.unpack) then return false end
  local site = nil
  if memory.read(KNOWN_DATE_GETTER, 8) == AOB_MODE then
    site = KNOWN_DATE_GETTER
  else
    site = num_addr(memory.search_process(AOB_MODE))
  end
  if not site or site < 0x10000 then L('date: getter pattern not found'); return false end
  if memory.read(site, 8) ~= AOB_MODE then L('date: unexpected getter bytes'); return false end
  local disp = memory.unpack('i32', memory.read(site + 3, 4))
  if not disp then L('date: bad getter displacement'); return false end
  DATE.global_ptr, DATE.ready = site + 7 + disp, true
  L(string.format('date: reader ready (global ptr at 0x%X)', DATE.global_ptr))
  return true
end

local function read_mode()
  if not DATE.ready and not install_date_reader() then return nil end
  local ctx = read_ptr_at(DATE.global_ptr)
  if not ctx then return nil end
  return read_ptr_at(ctx + 0x48)
end

local function unpack_career_data(raw)
  if not raw or #raw < 12 then return nil end
  -- 1. Bitfield layout (FL26 / FL27 and modern PES: year u16le, month u8, day u8)
  local y = raw:byte(1) + raw:byte(2) * 256
  local mo = raw:byte(3)
  local d = raw:byte(4)
  local identity = raw:byte(9) + raw:byte(10) * 256 + raw:byte(11) * 65536 + raw:byte(12) * 16777216
  local tid = math.floor(identity / 0x4000)
  if tid <= 0 or tid >= 65000 then tid = nil end

  if y >= 2000 and y <= 2200 and mo >= 1 and mo <= 12 and d >= 1 and d <= 31 then
    return y, mo, d, tid
  end

  -- 2. Decimal layout fallback (YYYYMMDD as u32le)
  local dec = raw:byte(1) + raw:byte(2) * 256 + raw:byte(3) * 65536 + raw:byte(4) * 16777216
  if dec >= 20000101 and dec <= 22001231 then
    y = math.floor(dec / 10000)
    mo = math.floor(dec / 100) % 100
    d = dec % 100
    if mo >= 1 and mo <= 12 and d >= 1 and d <= 31 then
      return y, mo, d, tid
    end
  end

  return nil
end

local function sync_career_identity(tid, y, raw)
  if not tid or tid <= 0 then return end
  local sig = '00000000'
  if raw and #raw >= 12 then
    -- raw[1..4] holds the calendar date (which advances daily).
    -- raw[5..12] holds the stable career struct / identity bits.
    sig = string.format('%08x', hash(raw:sub(5, 12)))
  else
    sig = string.format('%04d', y or 2027)
  end
  local active_id = string.format('ml_%04d_%s', tid, sig)
  if CAREER ~= active_id then
    CAREER = active_id
    write_file('career.txt', CAREER .. '\n')
    L('career identity synced to memory: ' .. CAREER)
    reset_career_state()
    if load_deal then load_deal() end
  end
end

local function read_career_info(mode)
  mode = mode or DATE.mode or read_mode()
  if not mode or mode < 0x10000 then return nil end
  for _, off in ipairs(CAREER_OFFSETS) do
    local raw = memory.read(mode + off, 12)
    if raw and #raw == 12 then
      local y, mo, d, tid = unpack_career_data(raw)
      if y then
        if tid and tid > 0 then
          sync_career_identity(tid, y, raw)
        end
        return y, mo, d, tid, off, mode
      end
    end
  end
  return nil
end

-- returns year, month, day, mode -- all nil when no career is loaded
local function game_date()
  local mode = read_mode()
  if not mode then return nil end
  DATE.mode = mode
  local y, mo, d, tid, off = read_career_info(mode)
  if y then
    DATE.off = off
    return y, mo, d, mode
  end
  return nil
end

-- The game's own team -> kit-folder map, used to put a readable name on the
-- office card and to resolve authentic GDB kits during Master League menus.
local GDB_MAP_LOADED = false
local GDB_MAP = {}
local MAP_NAMES = nil

local function load_gdb_map()
  if GDB_MAP_LOADED then return end
  GDB_MAP_LOADED = true
  local f = io.open(sider_path('content/kits/map.txt'), 'r') or io.open(DIR .. 'content/kits/map.txt', 'r')
  if not f then return end
  MAP_NAMES = MAP_NAMES or {}
  for line in f:lines() do
    local clean = line:gsub('#.*', '')
    local tid, folder = clean:match('^%s*(%d+)%s*,%s*"([^"]*)"')
    if not tid then tid, folder = clean:match('^%s*(%d+)%s*,%s*(%S+)') end
    tid = tonumber(tid)
    if tid and folder and #folder > 0 then
      folder = folder:gsub('^%s+', ''):gsub('%s+$', '')
      folder = folder:gsub('[\\/]+$', '')
      if #folder > 0 then
        GDB_MAP[tid] = folder
        local name = folder:match('([^\\/]+)$') or folder
        if #name > 0 then MAP_NAMES[tid] = name end
      end
    end
  end
  f:close()
end

local function is_national_team(tid)
  if not tid then return false end
  tid = tonumber(tid)
  if not tid or tid <= 0 then return false end
  -- Quick ID range checks for traditional national & classic teams in PES 2021
  if (tid >= 1 and tid <= 59) or (tid >= 900 and tid <= 908)
     or (tid >= 1550 and tid <= 1551) or (tid >= 2703 and tid <= 2704)
     or (tid >= 5439 and tid <= 5440) then
    return true
  end
  -- Check kitserver folder path in map.txt
  if not GDB_MAP_LOADED then load_gdb_map() end
  local folder = GDB_MAP[tid]
  if folder then
    local lower = folder:lower()
    if lower:find("national teams", 1, true) or lower:find("classics", 1, true) then
      return true
    end
  end
  return false
end

-- Read the human managed team ID directly from Master League memory
local function read_career_team(mode)
  local y, mo, d, tid = read_career_info(mode)
  if tid and tid > 0 and tid < 65000 and not is_national_team(tid) then
    return tid
  end
  return nil
end

local function is_in_ml(ctx)
  if STATE.in_edit_mode then return false end
  if ctx and ctx.tournament_id == 65535 then return false end
  if STATE.in_ml_flow == false then return false end
  local y, mo, d, mode = game_date()
  if y and mode then return true end
  if STATE.in_ml_flow == true then return true end
  return false
end

-- ===== managed club: auto-detection =======================================
-- The mod used to hard-code the club you manage (CFG.MANAGED_CLUB = 102, i.e.
-- Chelsea).  It now works the club out on its own, so a career can be started
-- with ANY team.  The layers, most authoritative first:
--
--   1. CFG.MANAGED_CLUB       a manual override (a number) always wins
--   2. club.txt               the club detected in an earlier session
--   3. the career learner     the team that turns up in EVERY career match
--                             (your club plays all of them; no other club does)
--   4. edit mode              the team being edited, only when nothing else has
--                             been found yet
--
-- Detection needs the live context, so it runs from set_teams (career matches),
-- set_home_team_for_kits (edit mode) and whenever the Sponsor Office is drawn.
-- The club's own kit colours are read from the game with ctx.kits.get(team, 0)
-- and written to club.txt, where the Python generator picks them up and paints
-- the kits in the club's real colours.
local CLUB_FILE = 'club.txt'

club_id = function()
  return STATE.club
end

local function club_source()
  return STATE.club_source or 'unknown'
end

local CLUB_SOURCE_LABEL = {
  saved = 'saved from last session',
  memory = 'auto-detected (career memory)',
  career = 'auto-detected in career',
  edit = 'from edit mode',
  unknown = 'not detected yet',
}
local function club_source_label()
  return CLUB_SOURCE_LABEL[club_source()] or tostring(club_source())
end

local function club_display_name(cid)
  cid = tonumber(cid) or club_id()
  if not cid then return 'not detected' end
  if not GDB_MAP_LOADED then load_gdb_map() end
  return (MAP_NAMES and MAP_NAMES[cid]) or ('Club #' .. tostring(cid))
end

local function resolve_authentic_gdb_kit(tid, slot_type, slot, target_suffix)
  if not GDB_MAP_LOADED then load_gdb_map() end
  local folder = GDB_MAP[tid]
  if not folder then return nil end

  slot = tonumber(slot) or 1
  slot_type = slot_type or "p"
  target_suffix = target_suffix or ""

  local norm_folder = folder:gsub('\\', '/')

  -- 1. Try exact slot (e.g. p1, p2, g1, etc.) with standard 4-digit formatting
  local rel = string.format("content/kits/%s/%s%d/u%04d%s%d%s.ftex", norm_folder, slot_type, slot, tid, slot_type, slot, target_suffix)
  local full = (DIR .. rel):gsub('/', '\\')
  local f = io.open(full, "rb") or io.open(DIR .. rel, "rb")
  if f then
    f:close()
    return rel
  end

  -- Try without leading zero padding (for rare teams with <4 digit IDs)
  local rel_raw = string.format("content/kits/%s/%s%d/u%d%s%d%s.ftex", norm_folder, slot_type, slot, tid, slot_type, slot, target_suffix)
  local full_raw = (DIR .. rel_raw):gsub('/', '\\')
  local f_raw = io.open(full_raw, "rb") or io.open(DIR .. rel_raw, "rb")
  if f_raw then
    f_raw:close()
    return rel_raw
  end

  -- 2. If requesting a font/number suffix for secondary slots (p2, p3, g2) and not found,
  -- check slot 1 font (standard PES kitserver fallback)
  if target_suffix ~= "" and slot > 1 then
    local rel_fb = string.format("content/kits/%s/%s1/u%04d%s1%s.ftex", norm_folder, slot_type, tid, slot_type, target_suffix)
    local full_fb = (DIR .. rel_fb):gsub('/', '\\')
    local f_fb = io.open(full_fb, "rb") or io.open(DIR .. rel_fb, "rb")
    if f_fb then
      f_fb:close()
      return rel_fb
    end

    local rel_fb_raw = string.format("content/kits/%s/%s1/u%d%s1%s.ftex", norm_folder, slot_type, tid, slot_type, target_suffix)
    local full_fb_raw = (DIR .. rel_fb_raw):gsub('/', '\\')
    local f_fb_raw = io.open(full_fb_raw, "rb") or io.open(DIR .. rel_fb_raw, "rb")
    if f_fb_raw then
      f_fb_raw:close()
      return rel_fb_raw
    end
  end

  return nil
end

-- read the club's kit colours straight out of the game.  ctx.kits.get answers
-- nil for teams the game has no licensed kit for (created / edited clubs), in
-- which case the Python resolver falls back to the kit map or a palette.
local function fetch_colors(ctx, team)
  team = tonumber(team)
  if not team or team <= 0 then return nil end
  local cached = STATE.colors[team]
  if cached then return cached end
  if not (ctx and ctx.kits and ctx.kits.get) then return nil end
  local k = ctx.kits.get(team, 0)
  if type(k) ~= 'table' then return nil end
  local c = { shirt1 = k.ShirtColor1, shirt2 = k.ShirtColor2, shorts = k.ShortsColor,
              socks = k.SocksColor, uni1 = k.UniColor_Color1, uni2 = k.UniColor_Color2 }
  if not (c.shirt1 or c.shirt2 or c.shorts or c.socks) then return nil end
  STATE.colors[team] = c
  return c
end

-- persist the detected club + its colours for the Python generator
local function save_club()
  local cid = club_id()
  if not cid then return false end
  local c = STATE.colors[cid] or {}
  return write_file(CLUB_FILE, string.format('%d|%s|%s|%s|%s|%s|%s|%s\n',
    cid, club_display_name(cid), c.shirt1 or '', c.shirt2 or '', c.shorts or '',
    c.socks or '', c.uni1 or '', c.uni2 or ''))
end

local function load_club_file()
  for _, line in ipairs(read_lines(CLUB_FILE)) do
    if #line > 0 and line:sub(1, 1) ~= '#' then
      local t = split(line)
      local cid = tonumber(t[1])
      if cid and cid > 0 and not is_national_team(cid) then
        STATE.club, STATE.club_source = cid, 'saved'
        STATE.club_name = (t[2] and #t[2] > 0) and t[2] or nil
        if t[3] and #t[3] > 0 then
          STATE.colors[cid] = { shirt1 = t[3], shirt2 = t[4] or '', shorts = t[5] or '',
                                socks = t[6] or '', uni1 = t[7] or '', uni2 = t[8] or '' }
        end
        L('club.txt: managed club #' .. tostring(cid) ..
          (STATE.club_name and (' (' .. STATE.club_name .. ')') or ''))
      end
    end
  end
end

local function set_club(cid, source, persist)
  cid = tonumber(cid)
  if not cid or cid <= 0 then return false end
  cid = math.floor(cid)
  if is_national_team(cid) then
    L(string.format('ignoring national/classic team #%d for managed club detection', cid))
    return false
  end
  if STATE.club ~= cid or STATE.club_source ~= source then
    STATE.club, STATE.club_source = cid, source or 'manual'
    L(string.format('managed club -> #%d (%s)', cid, tostring(STATE.club_source)))
  end
  if persist then save_club() end
  return true
end

-- Sponsor Office: type a club id by hand; this becomes the manual override
local function set_manual_club(cid)
  cid = tonumber(cid)
  if not cid or cid <= 0 or is_national_team(cid) then return false end
  CFG.MANAGED_CLUB = math.floor(cid)
  STATE.club, STATE.club_source = CFG.MANAGED_CLUB, 'manual'
  save_club()
  L('manual club override: #' .. tostring(CFG.MANAGED_CLUB))
  return true
end

local function clear_manual_club()
  CFG.MANAGED_CLUB = nil
  STATE.club_source = STATE.club and 'saved' or nil
  L('manual club override cleared - auto-detecting again')
end

-- ---- the career learner ---------------------------------------------------
-- Your club plays every one of your career matches; no other club does.  So
-- whichever team appears in (nearly) every career match is the one you manage.
local function record_match(home, away)
  home, away = tonumber(home), tonumber(away)
  if not home or not away or home == away then return end
  if is_national_team(home) or is_national_team(away) then return end
  STATE.votes[home] = (STATE.votes[home] or 0) + 1
  STATE.votes[away] = (STATE.votes[away] or 0) + 1
  STATE.matches = STATE.matches + 1
end

local function leader_team()
  local best, best_n, second_n = nil, 0, 0
  for t, n in pairs(STATE.votes) do
    if n > best_n then second_n, best, best_n = best_n, t, n
    elseif n > second_n then second_n = n end
  end
  return best, best_n, second_n
end

local function learn_club()
  if STATE.matches < 2 then return end
  local best, best_n, second_n = leader_team()
  if not best or best_n < 2 or best_n <= second_n then return end
  if STATE.club == best then return end
  if not STATE.club then
    set_club(best, 'career', true)
    return
  end
  local cur_n = STATE.votes[STATE.club] or 0
  -- a stale club.txt (the old club never plays) is replaced after a couple of
  -- matches, and a clear leader can also win out over a merely-possible one
  if (cur_n == 0 and STATE.matches >= 2) or (best_n >= 3 and best_n >= cur_n + 2) then
    set_club(best, 'career', true)
  end
end

local function detect_club(ctx)
  local mode = DATE.mode or read_mode()
  local mem_tid = read_career_team(mode)
  if mem_tid and mem_tid > 0 then
    if STATE.club ~= mem_tid then
      set_club(mem_tid, 'memory', true)
    end
    if ctx and not STATE.colors[mem_tid] and fetch_colors(ctx, mem_tid) then
      save_club()
    end
    return mem_tid
  end

  if type(CFG.MANAGED_CLUB) == 'number' and CFG.MANAGED_CLUB > 0 then
    if not STATE.colors[CFG.MANAGED_CLUB] and fetch_colors(ctx, CFG.MANAGED_CLUB) then
      save_club()
    end
    return club_id()
  end
  learn_club()
  local cid = club_id()
  if cid then
    local had = STATE.colors[cid]
    if fetch_colors(ctx, cid) and not had then save_club() end
  end
  return cid
end

-- ===== offers =============================================================
local function load_offers()
  OFFERS = {}
  local lines = read_lines('deals.txt')
  if #lines == 0 then L('deals.txt missing: Sponsor Office will be empty') end
  local n = 0
  for _, line in ipairs(lines) do
    if line:sub(1, 1) ~= '#' and #line > 0 then
      local t = split(line)
      local cid = tonumber(t[3])
      if cid then
        local clist = OFFERS[cid]
        if not clist then
          clist = {}
          OFFERS[cid] = clist
        end
        clist[#clist + 1] = {
          id = t[1], season = tonumber(t[2]), club = cid, brand = t[4],
          logo = path(t[5]), value = tonumber(t[6]), years = tonumber(t[7]), bonus = tonumber(t[8]), tier = t[9]
        }
        n = n + 1
      end
    end
  end
  for _, line in ipairs(read_lines('career.txt')) do
    if #line > 0 then CAREER = line end
  end
  L('loaded ' .. n .. ' offers across ' .. tostring(#lines) .. ' lines, career ' .. CAREER)
end

-- the brand pool, written by setup_watcher.py from the logos folder.  It is what
-- lets the mod offer deals to a club that deals.txt does not cover.
local function load_brands()
  BRANDS = {}
  for _, line in ipairs(read_lines('brands.txt')) do
    local b = line:gsub('^%s+', ''):gsub('%s+$', '')
    if #b > 0 and b:sub(1, 1) ~= '#' then BRANDS[#BRANDS + 1] = b end
  end
  if #BRANDS == 0 then
    L('brands.txt missing: clubs outside deals.txt cannot be offered a deal')
  end
end

-- Offers for a club deals.txt does not cover are synthesised here with the same
-- djb2 roll the rest of the mod uses, so they are identical on every reload and
-- every season.  Each season's five brands are a fresh window of the pool, five
-- on from the season before, so a club never sees the same brand two years
-- running (the rule deals.py enforces for the curated clubs).
local TIER_ORDER = { 'small', 'mid', 'big' }
local BASE_EUR = { small = 60000000, mid = 88000000, big = 135000000 }
local YEARS_PICK = { 1, 2, 2, 3 }
local BONUS_PICK = { 0, 5, 10 }

local function synth_offers(club, season, count)
  local out = {}
  local n = #BRANDS
  if n == 0 then return out end
  count = math.min(count or 5, n)
  local tier = TIER_ORDER[(hash('tier:' .. tostring(club)) % 3) + 1]
  local base = BASE_EUR[tier]
  local start = (hash('offers:' .. tostring(club)) + season * count) % n
  for i = 1, count do
    local key = tostring(club) .. ':' .. tostring(season) .. ':' .. tostring(i)
    local v = base * (0.85 + 0.30 * hash01('value:' .. key))
    out[#out + 1] = {
      id = string.format('%d-%d-%d', club, season, i),
      season = season, club = club,
      brand = BRANDS[((start + i - 1) % n) + 1],
      logo = path('logos/' .. BRANDS[((start + i - 1) % n) + 1] .. '.png'),
      value = math.floor(v / 100000 + 0.5) * 100000,
      years = YEARS_PICK[(hash('years:' .. key) % 4) + 1],
      bonus = BONUS_PICK[(hash('bonus:' .. key) % 3) + 1],
      tier = tier, synth = true,
    }
  end
  return out
end

local function visible()
  local out = {}
  local cid = club_id()
  if not cid then return out end
  if DEAL then return out end                 -- under contract: no new offers
  local clist = OFFERS[cid]
  if clist then
    for _, o in ipairs(clist) do
      if o.season == SEASON then out[#out + 1] = o end
    end
  end
  if #out == 0 then                           -- no curated set: make one
    out = synth_offers(cid, SEASON)
  end
  return out
end

-- ===== active deal (multi-season) =========================================
local function deal_end() return DEAL and (DEAL.start + DEAL.years - 1) or nil end

local function deal_active(season)
  if DEAL == nil then return false end
  local cid = club_id()
  if cid and DEAL.club ~= cid then return false end   -- a deal for another club
  return season >= DEAL.start and season <= deal_end()
end

local function career_deal_rel()
  if CAREER and CAREER ~= 'unknown' then
    return string.format('careers/%s/active_deal.txt', CAREER)
  end
  return 'active_deal.txt'
end

local function save_deal()
  local text = ''
  if DEAL then
    text = string.format('%s|%d|%s|%d|%d|%d|%s|%s|%d',
      DEAL.id, DEAL.club, DEAL.brand, DEAL.start, DEAL.years, DEAL.value,
      DEAL.tier or '', DEAL.signed_at or '', DEAL.bonus or 0)
  end
  write_file('active_deal.txt', text)
  if CAREER and CAREER ~= 'unknown' then
    write_file(career_deal_rel(), text)
  end
end

function load_deal()
  DEAL = nil
  local lines = {}
  if CAREER and CAREER ~= 'unknown' then
    lines = read_lines(career_deal_rel())
    if #lines == 0 then
      -- This career has never signed a deal in this profile.  The shared global
      -- file belongs to whichever career wrote it last - inheriting it would
      -- hand a brand-new save a sponsor it never signed for.  Wipe it and start
      -- clean: Season 2 then generates the sponsorless kit as intended.
      write_file('active_deal.txt', '')
      return
    end
  else
    lines = read_lines('active_deal.txt')
  end
  if #lines == 0 then return end
  local t = split(lines[1])
  local start, years, value = tonumber(t[4]), tonumber(t[5]), tonumber(t[6])
  if not (t[1] and t[3] and start and years) then return end
  DEAL = { id = t[1], club = tonumber(t[2]) or 0, brand = t[3], start = start,
           years = years, value = value or 0, tier = t[7] or '', signed_at = t[8] or '',
           bonus = tonumber(t[9]) or 0 }
  if DEAL.club and DEAL.club > 0 then
    OPTED_IN[DEAL.club] = true
  end
  L('active deal loaded [' .. tostring(CAREER) .. ']: ' .. DEAL.brand .. ' (' .. tostring(start) .. '..' .. tostring(deal_end()) .. ')')
end

local function load_opted_in()
  OPTED_IN = {}
  for _, line in ipairs(read_lines('opted_in.txt')) do
    local cid = tonumber(line:match('^%s*(%d+)%s*$'))
    if cid then OPTED_IN[cid] = true end
  end
  if DEAL and DEAL.club and DEAL.club > 0 then
    OPTED_IN[DEAL.club] = true
  end
end

local function save_opted_in()
  local lines = {}
  for cid, v in pairs(OPTED_IN) do
    if v then lines[#lines + 1] = tostring(cid) end
  end
  write_file('opted_in.txt', table.concat(lines, '\n'))
end

local function load_paid()
  PAID = {}
  for _, line in ipairs(read_lines('paid.txt')) do
    if #line > 0 then PAID[line] = true end
  end
end

-- A different career identity must never inherit the previous save's sponsor,
-- opt-in marker, payment ledger or request-dedup flags.  The shared
-- active_deal.txt is global (not career-owned), so clear it explicitly here;
-- opted_in.txt / paid.txt keep their own history but the in-memory maps start
-- fresh for the new save.
reset_career_state = function()
  DEAL = nil
  write_file('active_deal.txt', '')
  OPTED_IN = {}
  -- paid.txt keys are career-tagged (<career>:<club>:<season>:<brand>), so reload
  -- the ledger from disk instead of emptying it: switching back to an older save
  -- in the same session must not re-credit a season it was already paid for.
  load_paid()
  REQ_SEASONS, REQ_LEAGUE, JIT_REQUESTED = {}, {}, {}
  CLEAN, CLEAN_PENDING, WARNED = {}, {}, {}
  L('per-career state cleared for ' .. tostring(CAREER))
end

-- ===== budget: capture the club-budget pointer, then credit ===============
-- The game reads the manager's transfer budget here:
--     mov eax,[rdi+016ECBF4]      ; 8B 87 F4 CB 6E 01
--     mov [rbp-3C],eax            ; 89 45 C4
-- `rdi` is the club budget block and the two budgets live inside it:
--     transfer = [rdi + 016ECBF4]   (this instruction)
--     salary   = [rdi + 016ECC08]   (= transfer + 0x14)
-- Both offsets come from xAranaktu's PES2021 / Football Life cheat table, which
-- uses this exact AOB and these exact offsets.
--
-- We detour the instruction into a code cave, stash `rdi`, run the stolen
-- bytes, then jump back with an ABSOLUTE (FF 25) jump.  A Sider code cave is
-- not guaranteed to sit within the +/-2 GB reach of a rel32 jump, so a rel32
-- detour can silently corrupt the flow (crash).  The detour steals 17 bytes
-- (a clean instruction boundary) so the 14-byte absolute jump fits.
local BUDGET = { ready = false, attempted = false, slot = nil, disp = 0x16ECBF4, salary_disp = 0x16ECC08 }
local AOB_BUDGET = '\x8B\x87\xF4\xCB\x6E\x01\x89\x45\xC4'
-- the 8 bytes that follow the AOB (two `lea` instructions), completing the
-- 17-byte window we steal and then replay inside the cave
local AOB_BUDGET_TAIL = '\x48\x8D\x55\xC4\x48\x8D\x4D\xD0'
local BUDGET_STEAL = 17
local KNOWN_BUDGET_SITE = 0x140EA4C58
local BUDGET_FILE = 'budget_hook.txt'

local function load_budget_hook()
  local lines = read_lines(BUDGET_FILE)
  if lines and #lines > 0 then
    local t = split(lines[1])
    if #t >= 4 then
      local site = tonumber(t[1], 16)
      local cave = tonumber(t[2], 16)
      local slot = tonumber(t[3], 16)
      local disp = tonumber(t[4], 16)
      local sdisp = t[5] and tonumber(t[5], 16) or (disp + CFG.SALARY_DELTA)
      if site and site > 0x10000 and cave and cave > 0x10000 and slot and disp then
        -- Validate that the cached hook is actually active in this running process
        local jmp = memory and memory.read and memory.read(site, 6)
        if jmp == '\xFF\x25\x00\x00\x00\x00' then
          local target = read_ptr_at(site + 6)
          if target == cave then
            BUDGET.ready, BUDGET.slot = true, cave + slot
            BUDGET.disp, BUDGET.salary_disp = disp, sdisp
            L(string.format('budget hook loaded from verified cache (site=0x%X, slot=0x%X)', site, BUDGET.slot))
            return true
          end
        end
      end
    end
  end
  return false
end

local function save_budget_hook(site, cave, slot, disp, sdisp)
  write_file(BUDGET_FILE, string.format('%X|%X|%X|%X|%X\n',
    site, cave, slot, disp, sdisp))
end

local function install_budget_hook()
  if BUDGET.ready then return true end
  if BUDGET.attempted then return false end
  BUDGET.attempted = true

  -- Safe mode: read budget pointer directly from Master League mode context
  local mode = DATE.mode or read_mode()
  if mode and mode > 0x10000 then
    BUDGET.ready = true
    BUDGET.disp = 0x16ECBF4
    BUDGET.salary_disp = BUDGET.disp + CFG.SALARY_DELTA
    L(string.format('budget: ML direct mode ready at 0x%X (transfer +0x%X, salary +0x%X)',
      mode, BUDGET.disp, BUDGET.salary_disp))
    return true
  end
  return false
end

-- the exact club-budget pointer the game used, or DATE.mode fallback
local function budget_ptr()
  if BUDGET.ready and BUDGET.slot then
    local p = read_ptr_at(BUDGET.slot)
    if p and p > 0x10000 then return p end
  end
  local mode = DATE.mode or read_mode()
  if mode and mode > 0x10000 then
    local disp = BUDGET.disp or 0x16ECBF4
    local t = mread_u32(mode + disp)
    if t and t >= 0 and t < 0x7FFFFFFF then
      return mode
    end
  end
  return nil
end

-- add `units` (EUR100) to one u32 budget field; roll back if the write does
-- not read back.  Returns ok, err, before, after.
local function credit_field(addr, units, label)
  local before = mread_u32(addr)
  if not before or before == 0xFFFFFFFF or before == 0xCCCCCCCC then
    return false, label .. ' budget unreadable/implausible', before
  end
  local after = before + units
  if after > CFG.MAX_BUDGET then after = CFG.MAX_BUDGET end
  if after < 0 then after = 0 end
  memory.write(addr, memory.pack('u32', after))
  if mread_u32(addr) ~= after then
    memory.write(addr, memory.pack('u32', before))
    return false, label .. ' budget read-back mismatch', before
  end
  return true, nil, before, after
end

local function credit_budget(euros)
  if not CFG.CREDIT_BUDGET then return false, 'crediting disabled' end
  install_budget_hook()
  local career = budget_ptr()
  if not career then
    local m = DATE.mode or read_mode()
    if m then
      return false, string.format('career pointer not captured yet (mode=0x%X)', m)
    end
    return false, 'pointer not captured yet (no career loaded)'
  end
  euros = tonumber(euros) or 0
  if euros == 0 then return false, 'nothing to credit' end
  if DATE.mode and not BUDGET.checked then
    BUDGET.checked = true
    L(string.format('budget: rdi=0x%X  mode=0x%X  same=%s  transfer@rdi=%s  salary@rdi=%s',
      career, DATE.mode, tostring(career == DATE.mode),
      tostring(mread_u32(career + BUDGET.disp)),
      tostring(mread_u32(career + BUDGET.salary_disp))))
  end
  -- split the payment: TRANSFER_SHARE to the transfer budget, the rest to the
  -- salary budget (default 70% / 30%).  Each share is rounded to EUR100.
  local t_euros = math.floor(euros * CFG.TRANSFER_SHARE / CFG.MONEY_UNIT + 0.5) * CFG.MONEY_UNIT
  local s_euros = math.floor((euros - t_euros) / CFG.MONEY_UNIT + 0.5) * CFG.MONEY_UNIT
  local t_units = math.floor(t_euros / CFG.MONEY_UNIT)
  local s_units = math.floor(s_euros / CFG.MONEY_UNIT)
  if t_units == 0 and s_units == 0 then return false, 'nothing to move' end
  local parts = {}
  if t_units ~= 0 then
    local ok, why, before, after = credit_field(career + BUDGET.disp, t_units, 'transfer')
    if not ok then return false, why end
    parts[#parts + 1] = string.format('transfer %s -> %s', fmt_money(before * CFG.MONEY_UNIT), fmt_money(after * CFG.MONEY_UNIT))
  end
  if s_units ~= 0 then
    local ok, why, before, after = credit_field(career + BUDGET.salary_disp, s_units, 'salary')
    if not ok then return false, why end
    parts[#parts + 1] = string.format('salary %s -> %s', fmt_money(before * CFG.MONEY_UNIT), fmt_money(after * CFG.MONEY_UNIT))
  end
  return true, string.format('%s %s (%d%% transfer / %d%% salary): %s',
    euros > 0 and 'credited' or 'debited', fmt_money(math.abs(euros)),
    math.floor(CFG.TRANSFER_SHARE * 100 + 0.5), math.floor(CFG.SALARY_SHARE * 100 + 0.5),
    table.concat(parts, ', '))
end

-- ===== per-season deal upkeep =============================================
-- Called whenever the season is known/changes.  While a deal runs it asks the
-- watcher for a fresh kit (unique id per season, so it always rebuilds) and
-- credits that season's money exactly once.
-- the paid.txt ledger key for one season of the active deal (one payment each)
local function paid_key(season)
  return string.format('%s:%d:%d:%s', CAREER, DEAL.club, season, DEAL.brand)
end

local function has_user_kit(cid)
  if not cid or cid <= 0 then return false end
  local name = string.format('u%04dp1.ftex', cid)
  if CAREER and CAREER ~= 'unknown' then
    local cp = path('careers/' .. CAREER .. '/' .. name)
    local f = io.open(cp, 'rb') or io.open(DIR .. 'content/KitGenerator/careers/' .. CAREER .. '/' .. name, 'rb')
    if f then f:close(); return true end
  end
  local ap = path('active/' .. name)
  local f = io.open(ap, 'rb') or io.open(DIR .. 'content/KitGenerator/active/' .. name, 'rb')
  if f then f:close(); return true end
  return false
end

-- Clearing a deal is instant, but the watcher needs time to replace the old
-- branded .ftex files.  Queue a FORCED clean rebuild (the watcher normally
-- skips clean requests when a file with that name already exists).  The club
-- keeps wearing the dynamic pool while this runs - from Season 2 onwards it
-- must never fall back to an authentic kit because a rebuild is in flight.
local function request_clean_kit(club, season)
  if not club or club <= 0 then return end
  local key = club .. ':' .. season
  local req_id = string.format('clean-%d-%d-t%s', club, season, os.date('%Y%m%d%H%M%S'))
  CLEAN_PENDING[key] = { id = req_id, at = 0 }
  CLEAN[key] = true
  if CFG.ENABLE_KITS then
    append_line('kit_request.txt', string.format('%s|%d|%d||force|%s|%s',
      req_id, club, season, os.date('%Y-%m-%d %H:%M:%S'), CAREER or ''))
  end
  L('forced clean rebuild queued for club #' .. tostring(club) .. ' (season ' .. tostring(season) .. ')')
end

local function clean_request_done(req_id)
  if not req_id then return false end
  local f = io.open(DIR .. 'content/KitGenerator/watcher_state.txt', 'r')
  if not f then return false end
  local line
  repeat
    line = f:read('*l')
    if line and line == req_id then f:close(); return true end
  until not line
  f:close()
  return false
end

local function ensure_season_deal(season)
  season = season or SEASON or 2027
  -- Never act on a guessed season: at game load the calendar is not readable
  -- yet and SEASON would be the default, which would wrongly revert an active
  -- deal's kit to the clean one.  Wait until a real in-game date has been read.
  if not STATE.date_ok then return end
  local cid = club_id()

  -- A deal that belongs to a DIFFERENT club (you started a new career) must not
  -- carry over: release it and strip its logo from the old club's kit.
  if DEAL and cid and DEAL.club ~= cid then
    local old, brand = DEAL.club, DEAL.brand
    DEAL = nil
    REQ_SEASONS = {}
    REQ_LEAGUE = {}
    OPTED_IN[old] = nil
    save_deal()
    save_opted_in()
    L('deal with ' .. tostring(brand) .. ' belongs to club #' .. tostring(old) ..
      ' - released (now following #' .. tostring(cid) .. ')')
    request_clean_kit(old, season)
  end

  -- A contract that has run out must be released.  Otherwise `visible()` would
  -- keep hiding every offer (it returns nothing while DEAL is set) and the club
  -- could never sign a new sponsor again.  Persisted so it stays released.
  if DEAL and season > deal_end() then
    local brand, ended, old_club = DEAL.brand, deal_end(), DEAL.club
    DEAL = nil
    REQ_SEASONS = {}
    REQ_LEAGUE = {}
    OPTED_IN[old_club] = nil
    save_deal()                       -- blanks active_deal.txt
    save_opted_in()
    L('deal expired: ' .. tostring(brand) .. ' ended after season ' .. tostring(ended) ..
      ' - offers are open again')
    request_clean_kit(old_club, season)
  end

  if not cid then return end          -- club not detected yet: nothing to build

  local start_season = CFG.DYNAMIC_KIT_START_SEASON or 2028

  -- The old user-league pre-generation is intentionally gone.  Season rollover
  -- builds the lightweight p1/g1 baseline for every club; full secondary sets
  -- for AI clubs are generated only when that club is scheduled in an ML match.
  -- This keeps Exhibition authentic and avoids minutes of unused league work.

  if not deal_active(season) then
    -- Season 1: user team wears authentic default kit until a sponsor deal is signed.
    if season < start_season then
      L('season 1 (no deal active): user club #' .. tostring(cid) .. ' wears authentic default kit')
      return
    end

    -- Season 2+: user team gets a fresh sponsorless dynamic kit until a new deal
    -- is signed.  The clean rebuild is queued in the background; the existing
    -- active kit stays visible so the club never drops back to an authentic kit.
    local ckey = cid .. ':' .. season
    if CFG.ENABLE_KITS and not CLEAN[ckey] then
      request_clean_kit(cid, season)
      L('no deal for season ' .. tostring(season) ..
        ': requested sponsorless kit for user club #' .. tostring(cid))
    end
    return
  end
  local rkey = DEAL.club .. ':' .. season
  if CFG.ENABLE_KITS and not REQ_SEASONS[rkey] then
    REQ_SEASONS[rkey] = true
    local req_id = string.format('rebuild-%d-%s-%d', DEAL.club, DEAL.brand, season)
    append_line('kit_request.txt', string.format('%s|%d|%d|%s|%s|%s|%s',
      req_id, DEAL.club, season, DEAL.brand, DEAL.tier or '',
      os.date('%Y-%m-%d %H:%M:%S'), CAREER or ''))
    L('deal active: requested a fresh kit for season ' .. tostring(season))
  end
  if not CFG.ENABLE_SPONSORSHIP then return end
  local key = paid_key(season)
  if not PAID[key] then
    local ok, why = credit_budget(DEAL.value)
    if ok then
      PAID[key] = true
      append_line('paid.txt', key)
      L('budget: ' .. tostring(why))
    elseif not WARNED[season] then
      WARNED[season] = true
      L('budget credit deferred (' .. key .. '): ' .. tostring(why))
    end
  end
end

-- Bulk rollover is a Season-2+ concern only; Season 1 must keep every club on
-- its authentic licensed kit.
local function should_queue_rollover(season, prev)
  return CFG.ENABLE_KITS and prev and prev > 0
     and season >= (CFG.DYNAMIC_KIT_START_SEASON or 2028)
end

-- Refresh the in-game date/season from the ML calendar.  The season is named
-- for the year it ENDS in (Football Life 2027 == the 2026/27 season) and rolls
-- over in June, when the pre-season (Jun-Aug) opens.
local function refresh_date(ctx)
  local y, mo, d = game_date()
  if y then
    STATE.year, STATE.month, STATE.day = y, mo, d
    STATE.date_ok = true
    local prev = SEASON
    SEASON = (mo >= 6) and (y + 1) or y
    if prev ~= SEASON then
      L(string.format('season %d  (game date %04d-%02d-%02d)', SEASON, y, mo, d))
      if should_queue_rollover(SEASON, prev) then
        local req_id = string.format('season-%s-%d', CAREER or 'global', SEASON)
        local mode = CFG.ROLLOVER_MODE or "balanced"
        append_line('kit_request.txt', string.format('%s|0|%d|all|%s|%s|%s',
          req_id, SEASON, mode, os.date('%Y-%m-%d %H:%M:%S'), CAREER or ''))
        L(string.format('season rollover: queued AI dynamic kit update for season %d (mode=%s)', SEASON, mode))
      end
    end
  end
  detect_club(ctx)
  ensure_season_deal(SEASON)
end

-- ===== counter-offer rule (must equal kg_core.py) ========================
local function roll(career, season, offer_id, step)
  return (hash(career .. ':' .. season .. ':' .. offer_id .. ':' .. step) % 10000) / 10000
end
local TIER = { small = 0.8, mid = 1.0, big = 1.2 }
local ASKS = { 'Higher yearly value', 'Longer deal', 'Bigger bonus', 'Budget split' }
local ASK_PCT = { 0.15, 0.08, 0.20, 0.0 }
function m.counter_reply(career, season, offer_id, tier, ask_pct, step)
  local p = (0.70 - 2.0 * ask_pct - 0.15 * (step - 1)) * (TIER[tier] or 1.0)
  p = math.max(0.05, math.min(0.90, p))
  local r = roll(career, season, offer_id, step)
  if r < p then return 'accept' elseif r < p + 0.30 then return 'halfway' else return 'withdraw' end
end

-- ===== actions =============================================================
local function sign_offer(o)
  if SIGNED[o.id] then return end
  if DEAL then L('signing blocked: a deal with ' .. tostring(DEAL.brand) .. ' is already active'); return end
  if not in_signing_window() then
    local mn = STATE.month and MONTH_NAMES[STATE.month] or 'unknown'
    L('signing blocked: outside transfer window (current month: ' .. mn .. ')')
    return
  end
  SIGNED[o.id] = true
  append_line('signed.txt', string.format('%s|%s|%s', o.id, CAREER, os.date('%Y-%m-%d %H:%M:%S')))
  DEAL = { id = o.id, club = o.club, brand = o.brand, start = o.season, years = o.years or 1,
           value = o.value or 0, tier = o.tier, signed_at = os.date('%Y-%m-%d %H:%M:%S'),
           bonus = o.bonus or 0 }
  REQ_SEASONS = {}
  CLEAN_PENDING[o.club .. ':' .. o.season] = nil  -- a new deal supersedes any pending clean rebuild
  save_deal()
  if o.club and not OPTED_IN[o.club] then
    OPTED_IN[o.club] = true
    append_line('opted_in.txt', tostring(o.club))
    L('club #' .. tostring(o.club) .. ' opted into dynamic kit system')
  end
  L('signed ' .. o.id .. ' (' .. tostring(o.brand) .. ') for ' .. tostring(DEAL.years) ..
    ' season(s), ' .. fmt_money(DEAL.value) .. '/yr' ..
    ((DEAL.bonus > 0) and (', ' .. DEAL.bonus .. '% signing bonus') or ''))

  -- Immediately dispatch rebuild request to watcher with timestamp so it never deduplicates
  if CFG.ENABLE_KITS then
    local stamp = os.date('%Y%m%d%H%M%S')
    local req_id = string.format('rebuild-%d-%s-%d-t%s', DEAL.club, DEAL.brand, DEAL.start, stamp)
    append_line('kit_request.txt', string.format('%s|%d|%d|%s|%s|%s|%s',
      req_id, DEAL.club, DEAL.start, DEAL.brand, DEAL.tier or '', os.date('%Y-%m-%d %H:%M:%S'), CAREER))
    REQ_SEASONS[DEAL.club .. ':' .. DEAL.start] = true
    L('deal active: queued fresh kit rebuild (req=' .. req_id .. ')')
  end

  -- Credit yearly value immediately
  if CFG.ENABLE_SPONSORSHIP and CFG.CREDIT_BUDGET then
    local key = paid_key(DEAL.start)
    if not PAID[key] then
      local ok, why = credit_budget(DEAL.value)
      if ok then
        PAID[key] = true
        append_line('paid.txt', key)
        L('yearly sponsor value credited: ' .. tostring(why))
      else
        L('yearly sponsor credit deferred: ' .. tostring(why))
      end
    end
  end

  -- the signing bonus is a one-off, separate from the yearly value; ledger it
  -- under its own key so it can never be paid twice
  if CFG.ENABLE_SPONSORSHIP and CFG.CREDIT_BUDGET and (DEAL.bonus or 0) > 0 then
    local bonus = math.floor(DEAL.value * DEAL.bonus / 100 / CFG.MONEY_UNIT + 0.5) * CFG.MONEY_UNIT
    local bkey = paid_key(DEAL.start) .. ':bonus'
    if bonus > 0 and not PAID[bkey] then
      local ok, why = credit_budget(bonus)
      if ok then
        PAID[bkey] = true
        append_line('paid.txt', bkey)
        L('signing bonus (' .. DEAL.bonus .. '%): ' .. tostring(why))
      else
        L('signing bonus deferred: ' .. tostring(why))
      end
    end
  end
  CACHED_VISIBLE = nil
end

local function send_counter(o)
  local n = (SEL.rounds[o.id] or 0)
  if n >= 2 then SEL.reply = 'no more counters on this offer'; return end
  n = n + 1; SEL.rounds[o.id] = n
  SEL.reply = m.counter_reply(CAREER, o.season, o.id, o.tier, ASK_PCT[SEL.ask], n)
end

local function credit_now()
  if not DEAL then SEL.credit_msg = 'no active deal'; return end
  -- the office button is a retry for when the automatic credit had to defer;
  -- it must never pay the same season twice
  local key = paid_key(SEASON)
  if PAID[key] then
    SEL.credit_msg = 'already credited for season ' .. tostring(SEASON)
    L('manual credit skipped: ' .. SEL.credit_msg)
    return
  end
  local ok, why = credit_budget(DEAL.value)
  if ok then
    PAID[key] = true
    append_line('paid.txt', key)
  end
  SEL.credit_msg = (ok and 'OK: ' or 'FAILED: ') .. tostring(why)
  L('manual credit: ' .. SEL.credit_msg)
end

-- early-exit clause: end the deal now, pay a share of the value still to run
-- (CFG.TERMINATION_PCT) as a buyout, and take the sponsor off the kit at once
local function terminate_deal()
  if not DEAL then SEL.credit_msg = 'no active deal'; return end
  local season = SEASON
  local last = deal_end()
  local remaining = (last and last >= season) and (last - season + 1) or 0
  local buyout = math.floor(DEAL.value * CFG.TERMINATION_PCT * remaining / CFG.MONEY_UNIT + 0.5) * CFG.MONEY_UNIT
  local note = ''
  if CFG.ENABLE_SPONSORSHIP and CFG.CREDIT_BUDGET and buyout > 0 then
    local ok, why = credit_budget(-buyout)
    note = (ok and 'buyout paid (' or 'buyout failed (') .. tostring(why) .. ')'
    L('terminate: ' .. note)
  end
  local brand = DEAL.brand
  local club = DEAL.club
  DEAL = nil
  REQ_SEASONS = {}
  OPTED_IN[club] = nil
  save_deal()                       -- blanks active_deal.txt
  save_opted_in()
  request_clean_kit(club, season)    -- forced clean: the old branded file still exists
  SEL.credit_msg = 'terminated ' .. tostring(brand) .. (note ~= '' and ('; ' .. note) or '')
  L('terminated deal with ' .. tostring(brand) .. (note ~= '' and (' (' .. note .. ')') or ''))
end

-- ===== Sider Mod Menu page (native) =======================================
local CACHED_VISIBLE = nil
local CACHED_CID = nil
local CACHED_SEASON = nil
local OFFICE_TICKS = 0

local function get_cached_visible(cid, season)
  if CACHED_VISIBLE and CACHED_CID == cid and CACHED_SEASON == season then
    return CACHED_VISIBLE
  end
  local full = visible()
  local list = {}
  for i = 1, math.min(4, #full) do
    list[#list + 1] = full[i]
  end
  CACHED_VISIBLE = list
  CACHED_CID = cid
  CACHED_SEASON = season
  return CACHED_VISIBLE
end

local function build_office(ui, ctx)
  OFFICE_TICKS = OFFICE_TICKS + 1
  if OFFICE_TICKS % 30 == 0 or not STATE.date_ok then
    refresh_date(ctx)
  end

  local in_ml = is_in_ml(ctx)
  local cid = detect_club(ctx)
  local mn = STATE.month and MONTH_NAMES[STATE.month] or 'Pre-season'
  local window_open = in_signing_window()

  -- Sleek Executive Club Banner
  ui:section('Club Identity', 'trophy', 'Master League Sponsor Operations')
  ui:cols(0.5)
  ui:kv('Managed Club', cid and club_display_name(cid) or 'Detecting...', cid and 'accent' or 'warn')
  ui:kv('Club ID', cid and ('#' .. tostring(cid)) or '-')
  ui:nextcol()
  ui:kv('Season', tostring(SEASON) .. ' (' .. mn .. ')')
  ui:kv('Transfer Window', window_open and 'OPEN' or 'CLOSED', window_open and 'ok' or 'warn')
  ui:endcols()

  if not in_ml and not STATE.date_ok then
    ui:message('Enter Master League to manage dynamic sponsors and kits.', 'info')
    return
  end
  if not cid then
    ui:message('Detecting your club from Master League memory...', 'warn')
    return
  end

  -- ---- Executive sponsorship card ----------------------------------------
  if DEAL then
    local seasons = DEAL.years or 1
    local last = deal_end() or DEAL.start
    local elapsed = math.max(1, math.min(seasons, SEASON - DEAL.start + 1))
    local bonus = math.floor(DEAL.value * (DEAL.bonus or 0) / 100 / CFG.MONEY_UNIT + 0.5) * CFG.MONEY_UNIT
    local pct = math.floor(100 * elapsed / seasons + 0.5)

    ui:section('Active Sponsorship', 'tag', 'Season ' .. tostring(SEASON))

    ui:cols(0.32)
    ui:image(DEAL.logo or path('logos/' .. DEAL.brand .. '.png'), nil, 64)
    ui:nextcol()
    ui:text(string.upper(tostring(DEAL.brand)), 'bold')
    ui:text(tier_label(DEAL.tier), 'small')
    ui:kv('Yearly value', fmt_money(DEAL.value), 'accent')
    ui:endcols()

    local p1_ftex = (DIR .. string.format('content/KitGenerator/active/u%04dp1.ftex', DEAL.club)):gsub('/', '\\')
    local f_kit = io.open(p1_ftex, 'rb')
    local kit_ready = false
    if f_kit then f_kit:close(); kit_ready = true end

    ui:space(4)
    ui:cols(0.34)
    ui:kv('Contract', tostring(DEAL.start) .. ' - ' .. tostring(last))
    ui:kv('Length', plural(seasons, 'season'))
    ui:nextcol()
    ui:kv('Signing bonus', (DEAL.bonus or 0) > 0 and (tostring(DEAL.bonus) .. '%  (' .. fmt_money(bonus) .. ')') or 'none')
    ui:kv('Dynamic Kit', kit_ready and 'Ready (Active)' or 'Generating...', kit_ready and 'ok' or 'warn')
    ui:nextcol()
    ui:kv('Status', 'Active', 'ok')
    ui:kv('Season', 'year ' .. tostring(elapsed) .. ' of ' .. tostring(seasons))
    ui:endcols()

    ui:space(4)
    ui:kv('Contract progress', progress_bar(elapsed, seasons) .. '  ' .. tostring(pct) .. '%')

    if kit_ready then
      ui:message('Dynamic Kit is active & ready for ' .. club_display_name(DEAL.club) .. '! It will appear in your next match.', 'ok')
    else
      ui:message('Under contract. Kit generator is preparing your kit files...', 'info')
    end
    ui:row()
    ui:button('credit', 'Credit this season\'s money now', function() credit_now() end, 'primary', 'check')
    ui:button('term', SEL.term_confirm and 'Confirm termination' or 'Terminate contract',
      function()
        if SEL.term_confirm then SEL.term_confirm = false; terminate_deal()
        else SEL.term_confirm = true end
      end, 'ghost', 'edit')
    ui:endrow()
    if SEL.term_confirm then
      ui:message('Press again to confirm. The deal ends now, a buyout (' ..
        math.floor(CFG.TERMINATION_PCT * 100 + 0.5) .. '% of the value still to run) is taken ' ..
        'from your budget, and the logo comes off the kit.', 'warn')
    end
    if SEL.credit_msg then ui:message(SEL.credit_msg, 'info') end
    return
  end

  -- ---- Offers ------------------------------------------------------------
  local list = get_cached_visible(cid, SEASON)
  local mn = STATE.month and MONTH_NAMES[STATE.month] or 'unknown'
  local window_open = in_signing_window()

  ui:section('Sponsor Offers', 'trophy', 'Season ' .. tostring(SEASON) .. '  -  ' .. plural(#list, 'offer'))

  local kit_ready = has_user_kit(cid)
  local start_season = CFG.DYNAMIC_KIT_START_SEASON or 2028
  local pending_key = cid and (cid .. ':' .. SEASON) or nil
  if pending_key and CLEAN_PENDING[pending_key] then
    ui:message('Contract ended. A sponsorless kit is being rebuilt; it will appear at the next match.', 'info')
  elseif deal_active(SEASON) and DEAL then
    ui:message('Club is wearing the ' .. tostring(DEAL.brand) ..
      ' dynamic kit with sleeve branding. A fresh set is generated for each season of the deal.', 'ok')
  elseif SEASON < start_season then
    ui:message('Season 1: all clubs wear their authentic licensed kits. Sign an offer below to switch this club to a dynamic sponsored kit immediately.', 'info')
  elseif kit_ready then
    ui:message('Club is wearing a sponsorless dynamic kit while awaiting a sponsor agreement. Sign an offer below to add a sponsor logo.', 'ok')
  else
    ui:message('Club dynamic kit is generating (sponsorless)... It will appear in your next match.', 'info')
  end

  if window_open then
    ui:message('Transfer window OPEN (' .. mn .. '). You may sign deals now.', 'ok')
  else
    local mn_list = {}
    for _, mm in ipairs(CFG.SIGNING_MONTHS) do mn_list[#mn_list + 1] = MONTH_NAMES[mm] end
    ui:message('Transfer window CLOSED (' .. mn .. '). Signing is allowed only in ' ..
      table.concat(mn_list, ', ') .. '.', 'warn')
  end
  if #list == 0 then
    ui:text('No offers available for your club this season.', 'muted')
  end

  for i, o in ipairs(list) do
    ui:cols(0.28)
    ui:image(o.logo, nil, 48)
    ui:nextcol()
    ui:text(string.upper(tostring(o.brand)), 'bold')
    ui:text(tier_label(o.tier), 'small')
    ui:kv('Per year', fmt_money(o.value), 'accent')
    ui:endcols()
    ui:kv('Length', plural(o.years, 'season'))
    ui:kv('Signing bonus', (o.bonus or 0) > 0 and (tostring(o.bonus) .. '%') or 'none')
    ui:row()
    ui:button('sign' .. i, SIGNED[o.id] and 'Signed' or 'Sign deal', function() sign_offer(o) end,
      'primary', 'check', not SIGNED[o.id])
    ui:button('ctr' .. i, 'Counter offer', function() SEL.counter = i; SEL.reply = nil end, 'ghost', 'edit')
    ui:endrow()
    if i < #list then ui:separator() end
  end

  local o = list[SEL.counter]
  if o then
    ui:section('Counter: ' .. string.upper(tostring(o.brand)), 'edit', 'Ask the sponsor to improve the terms')
    ui:choice('ask', 'Ask for', ASKS, SEL.ask, function(i) SEL.ask = i end)
    ui:button('send', 'Send counter offer', function() send_counter(o) end, 'primary', 'play')
    if SEL.reply then ui:message('Sponsor answer: ' .. SEL.reply, 'info') end
  end
end

-- ===== classic overlay fallback (text + keys) ==============================
local function pad(s, n)
  s = tostring(s)
  if #s >= n then return s:sub(1, n) end
  return s .. string.rep(' ', n - #s)
end

function m.overlay_on(ctx)
  if not OFFICE.open then return '' end
  refresh_date(ctx)
  local mn = STATE.month and MONTH_NAMES[STATE.month] or 'unknown'
  local win_open = in_signing_window()
  local club_name = club_display_name(club_id())
  local bar = string.rep('=', 78)
  local sep = string.rep('-', 78)

  local lines = {}
  lines[#lines + 1] = bar
  lines[#lines + 1] = '  SPONSOR OFFICE  -  ' .. club_name .. '  -  Season ' .. tostring(SEASON)
  lines[#lines + 1] = '  Window: [' .. (win_open and 'OPEN' or 'CLOSED') .. ' - ' .. mn .. ']'
  lines[#lines + 1] = bar

  if DEAL then
    lines[#lines + 1] = '  ACTIVE DEAL: ' .. DEAL.brand .. '   ' .. fmt_money(DEAL.value) .. '/yr'
    lines[#lines + 1] = '  Runs: season ' .. tostring(DEAL.start) .. ' - ' .. tostring(deal_end())
    if (DEAL.bonus or 0) > 0 then
      lines[#lines + 1] = '  Signing bonus: ' .. tostring(DEAL.bonus) .. '% (' ..
        fmt_money(math.floor(DEAL.value * DEAL.bonus / 100 / CFG.MONEY_UNIT + 0.5) * CFG.MONEY_UNIT) .. ')'
    end
    lines[#lines + 1] = '  No new offers while the deal runs; a new kit is built each season.'
    lines[#lines + 1] = sep
    lines[#lines + 1] = '  [C] credit this season\'s money  [T] terminate contract  [Esc] close'
    lines[#lines + 1] = bar
    return table.concat(lines, '\n')
  end

  lines[#lines + 1] = '  ' .. pad('BRAND', 16) .. pad('VALUE/YR', 16) .. pad('LENGTH', 10) .. pad('BONUS', 10) .. 'STATUS'
  lines[#lines + 1] = sep
  local list = visible()
  if #list == 0 then
    lines[#lines + 1] = '  (no offers available for this club)'
  else
    for i, o in ipairs(list) do
      local marker = (i == OFFICE.sel) and '>>' or '  '
      local status = SIGNED[o.id] and 'SIGNED' or 'available'
      lines[#lines + 1] = marker .. ' ' .. pad(o.brand, 14) .. pad(fmt_money(o.value), 16) ..
        pad(tostring(o.years) .. 'y', 10) .. pad(tostring(o.bonus) .. '%', 10) .. status
    end
  end
  lines[#lines + 1] = sep
  if not win_open then
    local mn_list = {}
    for _, mm in ipairs(CFG.SIGNING_MONTHS) do mn_list[#mn_list + 1] = MONTH_NAMES[mm] end
    lines[#lines + 1] = '  Signing allowed only in the pre-season: ' .. table.concat(mn_list, ', ')
    lines[#lines + 1] = '  Press F11 to manually confirm transfer window'
  else
    lines[#lines + 1] = '  Press Enter to sign the highlighted offer'
  end
  lines[#lines + 1] = '  [Up/Down] select  [Enter] sign  [F11] window toggle  [Esc] close'
  lines[#lines + 1] = bar
  return table.concat(lines, '\n')
end

function m.key_down(ctx, vk)
  local handled = false
  if vk == CFG.MODE_KEY then
    STATE.manual_ml = not STATE.manual_ml
    L('manual Master League mode: ' .. tostring(STATE.manual_ml))
    handled = true
  elseif vk == CFG.WINDOW_KEY then
    STATE.manual_window = not STATE.manual_window
    L('manual transfer window: ' .. tostring(STATE.manual_window))
    handled = true
  elseif vk == CFG.OFFICE_KEY then
    OFFICE.open = not OFFICE.open
    handled = true
  elseif OFFICE.open then
    if vk == 0x26 then OFFICE.sel = math.max(1, OFFICE.sel - 1); handled = true
    elseif vk == 0x28 then OFFICE.sel = math.min(math.max(1, #visible()), OFFICE.sel + 1); handled = true
    elseif vk == 0x0D and visible()[OFFICE.sel] then sign_offer(visible()[OFFICE.sel]); handled = true
    elseif vk == 0x43 and DEAL then credit_now(); handled = true
    elseif vk == 0x54 and DEAL then           -- [T] terminate (press twice)
      if SEL.term_confirm then SEL.term_confirm = false; terminate_deal()
      else SEL.term_confirm = true; L('press T again to confirm termination') end
      handled = true
    elseif vk == 0x1B then OFFICE.open = false; SEL.term_confirm = false; handled = true end
  end
  if handled and ctx then ctx.consumed = true end
end

local function ensure_opponent_kits(opp_id)
  opp_id = tonumber(opp_id)
  if not opp_id or opp_id <= 0 then return end
  if is_national_team(opp_id) then return end
  local start_season = CFG.DYNAMIC_KIT_START_SEASON or 2028
  local cid = club_id()
  -- From Season 2 the human club's kit is owned by the deal/clean rebuild path.
  -- A JIT request would call generate_club_kits() with an AI sponsor and wipe it.
  if SEASON >= start_season and opp_id == cid then return end
  -- In Season 1:
  -- - AI clubs wear authentic kits (no dynamic generation)
  -- - User club wears authentic unless they signed a deal
  if SEASON < start_season then
    if opp_id ~= cid then return end
    if not deal_active(SEASON) then return end
  end
  if not CFG.ENABLE_KITS then return end

  -- The p1/g1 baseline comes from the season rollover, but a club may still be
  -- new, missed by that pass, or missing a secondary slot.  ANY missing slot
  -- means the scheduled opponent needs a JIT rebuild; checking only p2 used to
  -- leave clubs with a partial set on away/third kits.
  for _, scode in ipairs({ 'p1', 'g1', 'p2', 'p3', 'g2' }) do
    local sname = string.format("content/KitGenerator/active/u%04d%s.ftex", opp_id, scode)
    local full = (DIR .. sname):gsub('/', '\\')
    local f = io.open(full, "rb") or io.open(DIR .. sname, "rb") or io.open(sider_path(sname), "rb")
    if not f then
      local jkey = opp_id .. ':' .. SEASON
      if not JIT_REQUESTED[jkey] then
        JIT_REQUESTED[jkey] = true
        local req_id = string.format('jit-%d-%d', opp_id, SEASON)
        append_line('kit_request.txt', string.format('%s|%d|%d|all|jit|%s|%s',
          req_id, opp_id, SEASON, os.date('%Y-%m-%d %H:%M:%S'), CAREER or ''))
        L(string.format('calendar schedule: queued JIT kit generation for scheduled club #%d (season %d, missing %s)',
          opp_id, SEASON, scode))
      end
      return
    end
    f:close()
  end
end

-- ===== undersleeve & kit details sync =====================================
local orig_kits_set = nil
local orig_kits_set_gk = nil

local function read_kit_meta(tid, slot_str)
  local candidates = {}
  local cid = club_id()
  if cid and tid == cid and CAREER and CAREER ~= 'unknown' then
    candidates[#candidates + 1] = string.format('careers/%s/u%04d%s.json', CAREER, tid, slot_str)
  end
  candidates[#candidates + 1] = string.format('active/u%04d%s.json', tid, slot_str)

  for _, rel in ipairs(candidates) do
    local lines = read_lines(rel)
    if #lines > 0 then
      local meta = {}
      for _, line in ipairs(lines) do
        for key, val in line:gmatch('"([%w_]+)"%s*:%s*"([^"]+)"') do
          meta[key] = val
        end
        for key, val in line:gmatch('"([%w_]+)"%s*:%s*(%d+)') do
          meta[key] = tonumber(val) or val
        end
      end
      if meta.undershirt_color or meta.collar_model then
        return meta
      end
    end
  end
  return nil
end

local function get_slot_code(kit_id, cfg, is_gk)
  if cfg and cfg.KitFile then
    local code = tostring(cfg.KitFile):match("([pg]%d+)")
    if code then return code end
  end
  if is_gk then return "g1" end
  return string.format("p%d", (kit_id or 0) + 1)
end

local function sync_undershirt_color(ctx, team_id, kit_id, cfg, is_gk)
  if not cfg or not team_id then return end
  local slot_code = get_slot_code(kit_id, cfg, is_gk)
  local meta = read_kit_meta(team_id, slot_code)
  if meta then
    if meta.undershirt_color then
      local old_col = cfg.UndershirtColor
      cfg.UndershirtColor = meta.undershirt_color
      cfg.UniColor_Color1 = meta.undershirt_color
      cfg.UniColor_Color2 = meta.undershirt_color
      L(string.format("undersleeve sync for team %d [%s]: %s -> %s (UniColor synced)", team_id, slot_code, tostring(old_col), tostring(cfg.UndershirtColor)))
    end
    if meta.shirt_color_1 then
      cfg.ShirtColor1 = meta.shirt_color_1
      if not meta.undershirt_color then
        cfg.UniColor_Color1 = meta.shirt_color_1
      end
    end
    if meta.shirt_color_2 then cfg.ShirtColor2 = meta.shirt_color_2 end
    if meta.shorts_color then cfg.ShortsColor = meta.shorts_color end
    if meta.socks_color then cfg.SocksColor = meta.socks_color end
    if meta.collar_model then
      local c_val = tonumber(meta.collar_model)
      if c_val and c_val > 0 then
        local old_collar = cfg.Collar
        cfg.Collar = c_val
        cfg.WinterCollar = c_val
        L(string.format("collar model sync for team %d [%s]: %s -> %d", team_id, slot_code, tostring(old_collar), c_val))
      end
    end
  end
end

local function install_undersleeve_hook(ctx)
  if not (ctx and ctx.kits and ctx.kits.set) then return end
  if orig_kits_set then return end

  orig_kits_set = ctx.kits.set
  ctx.kits.set = function(team_id, kit_id, cfg, radar_flag)
    if is_in_ml(ctx) and not is_national_team(team_id) and cfg then
      sync_undershirt_color(ctx, team_id, kit_id, cfg, false)
    end
    return orig_kits_set(team_id, kit_id, cfg, radar_flag)
  end

  if ctx.kits.set_gk then
    orig_kits_set_gk = ctx.kits.set_gk
    ctx.kits.set_gk = function(team_id, cfg)
      if is_in_ml(ctx) and not is_national_team(team_id) and cfg then
        sync_undershirt_color(ctx, team_id, 0, cfg, true)
      end
      return orig_kits_set_gk(team_id, cfg)
    end
  end
  L("undersleeve sync hook installed on ctx.kits.set and ctx.kits.set_gk")
end

-- Every match the game sets up tells us which two clubs are playing.  A career
-- fixture is the strong signal (your club plays them all); a friendly
-- (tournament_id 65535) is ignored so exhibition opponents cannot muddy the
-- vote.  We also grab both sides' kit colours while the game is holding them.
function m.set_teams(ctx, home, away)
  if not WATCHER_STARTED and CFG.START_PROCESS and CFG.ENABLE_KITS then
    start_watcher()
  end
  if CFG.ENABLE_SPONSORSHIP and CFG.CREDIT_BUDGET and not BUDGET.attempted then
    install_budget_hook()
  end
  install_undersleeve_hook(ctx)
  STATE.in_edit_mode = false
  local career = not (ctx and ctx.tournament_id == 65535)
  if career then
    STATE.in_ml_flow = true
    if not is_national_team(home) and not is_national_team(away) then
      record_match(home, away)
      fetch_colors(ctx, home)
      fetch_colors(ctx, away)
      ensure_opponent_kits(home)
      ensure_opponent_kits(away)
    end
  else
    STATE.in_ml_flow = false
  end
  refresh_date(ctx)
end

-- Edit mode is the last-resort signal: only when no club has been found any
-- other way do we assume the team being edited is the one you manage.
function m.set_home_team_for_kits(ctx, team_id, edit_mode)
  STATE.in_edit_mode = (edit_mode == 1)
  if edit_mode == 1 and not club_id() then set_club(team_id, 'edit', true) end
  fetch_colors(ctx, team_id)
  refresh_date(ctx)
end

function m.make_key(ctx, filename)
  if not CFG.ENABLE_KITS then return nil end
  if not filename then return nil end

  -- Track UI flow state between Master League and Exhibition/Main Menu
  if string.find(filename, "common\\script\\flow\\", 1, true) then
    if string.find(filename, "\\ML\\", 1, true) then
      STATE.in_ml_flow = true
    elseif string.find(filename, "\\Exhibition\\", 1, true)
        or string.find(filename, "\\Top\\", 1, true)
        or string.find(filename, "\\Edit\\", 1, true)
        or string.find(filename, "\\BL\\", 1, true) then
      STATE.in_ml_flow = false
    end
    return nil
  end

  if not string.find(filename, "%.ftex$") then return nil end

  -- Master League only: Exhibition matches (65535) and non-ML modes never receive dynamic kits
  if STATE.in_edit_mode then return nil end
  if ctx and ctx.tournament_id == 65535 then return nil end
  if not is_in_ml(ctx) then return nil end

  local lower = filename:lower()
  local tid, slot_type, slot, suffix = string.match(lower, "[ku]0*(%d+)([pg])(%d)([_%a%d]*)%.ftex$")
  if not tid or not slot_type or not slot then return nil end
  tid = tonumber(tid)
  if is_national_team(tid) then
    return nil
  end
  slot = tonumber(slot)
  if slot_type == "p" then
    if slot < 1 or slot > 3 then return nil end
  elseif slot_type == "g" then
    if slot < 1 or slot > 2 then return nil end
  else
    return nil
  end

  local cid = club_id()
  if not cid or cid <= 0 then
    cid = detect_club(ctx)
  end
  local needs_authentic = false
  local start_season = CFG.DYNAMIC_KIT_START_SEASON or 2028
  local is_season_1 = (SEASON < start_season)
  local is_user = (cid and cid > 0 and tid == cid)

  if is_season_1 then
    if is_user and deal_active(SEASON) then
      -- Season 1: User signed a sponsor deal -> wear dynamic kit with that sponsor
      needs_authentic = false
      if not STATE.date_ok or not has_user_kit(cid) then
        refresh_date(ctx)
      end
    else
      -- Season 1: All clubs (AI clubs and user club without an active deal) wear authentic default kits
      needs_authentic = true
    end
  else
    -- Season 2 onwards: All clubs (AI and user club) wear dynamic kits
    -- User club gets sponsorless dynamic kit if no active deal, or branded kit if deal active
    needs_authentic = false
    if is_user and (not STATE.date_ok or not has_user_kit(cid)) then
      refresh_date(ctx)
    end
  end

  -- Deal expiry only queues a background clean rebuild.  From Season 2 the
  -- human club must stay in the dynamic pool, so never drop back to an
  -- authentic kit while that rebuild is in flight.  This check just retires the
  -- UI "rebuilding" notice once the watcher records the request as done.
  if is_user and cid then
    local pk = cid .. ':' .. SEASON
    local pending = CLEAN_PENDING[pk]
    if pending then
      local now = os.time()
      if now - pending.at >= 2 then
        pending.at = now
        if clean_request_done(pending.id) then CLEAN_PENDING[pk] = nil end
      end
    end
  end

  local suffix_map = {
    [""] = "",
    ["_b"] = "_back",
    ["_back"] = "_back",
    ["_l"] = "_leg",
    ["_leg"] = "_leg",
    ["_n"] = "_name",
    ["_name"] = "_name",
    ["_n_ex"] = "_name_ex",
    ["_name_ex"] = "_name_ex",
    ["_c"] = "_chest",
    ["_chest"] = "_chest",
  }

  local target_suffix = suffix_map[suffix or ""]
  if not target_suffix then return nil end

  -- If authentic kit is required (Season 1 AI, or un-opted user club), resolve from GDB kits
  if needs_authentic then
    local gdb_path = resolve_authentic_gdb_kit(tid, slot_type, slot, target_suffix)
    if gdb_path then
      if target_suffix == "" then
        L(string.format('serving authentic GDB kit (ML cold-boot resolver): %s -> %s', filename, gdb_path))
      else
        L(string.format('serving authentic GDB font (ML cold-boot resolver): %s -> %s', filename, gdb_path))
      end
      return gdb_path
    end
    return nil
  end

  local rel_path = nil

  -- 1. Check career-specific isolated profile first (if this is the managed human club)
  if cid and tid == cid and CAREER and CAREER ~= 'unknown' then
    local career_cand = string.format("content/KitGenerator/careers/%s/u%04d%s%d%s.ftex", CAREER, tid, slot_type, slot, target_suffix)
    local career_full = (DIR .. career_cand):gsub('/', '\\')
    local cf = io.open(career_full, "rb") or io.open(DIR .. career_cand, "rb")
    if cf then
      cf:close()
      rel_path = career_cand
    end
  end

  -- 2. Fall back to global pre-generated active pool
  if not rel_path then
    local global_cand = string.format("content/KitGenerator/active/u%04d%s%d%s.ftex", tid, slot_type, slot, target_suffix)
    local global_full = (DIR .. global_cand):gsub('/', '\\')
    local gf = io.open(global_full, "rb") or io.open(DIR .. global_cand, "rb")
    if gf then
      gf:close()
      rel_path = global_cand
    end
  end

  if rel_path then
    if target_suffix == "" then
      local label = (slot_type == "g") and ("dynamic GK" .. tostring(slot) .. " kit") or ("dynamic kit")
      L(string.format('serving %s (ML mode): %s -> %s', label, filename, rel_path))
    else
      L(string.format('serving dynamic contrasting font (ML mode): %s -> %s', filename, rel_path))
    end
    return rel_path
  else
    -- Fallback to authentic GDB kit if dynamic kit file is unexpectedly missing
    -- JIT generation assigns an AI sponsor to whoever it builds for.  Never let
    -- it touch the human club: that is how an un-signed sponsor kit appeared in
    -- Season 2 and then kept coming back after a new deal was signed.
    if not needs_authentic and target_suffix == "" and tid ~= cid
       and (slot > 1 or slot_type == "g") then
      ensure_opponent_kits(tid)
    end
    local gdb_fb = resolve_authentic_gdb_kit(tid, slot_type, slot, target_suffix)
    if gdb_fb then
      L(string.format('serving authentic GDB fallback (dynamic kit missing): %s -> %s', filename, gdb_fb))
      return gdb_fb
    end
  end
  return nil
end

function m.get_filepath(ctx, filename, key)
  if key and (string.find(key, "content/KitGenerator/", 1, true) or string.find(key, "content\\KitGenerator\\", 1, true)
           or string.find(key, "content/kits/", 1, true) or string.find(key, "content\\kits\\", 1, true)) then
    local full = ((DIR .. key):gsub('/', '\\'))
    L(string.format('serving kit file: %s', full))
    return full
  end
  return nil
end

-- ===== background kit watcher =============================================
local WATCHER_STARTED = false
start_watcher = function()
  if WATCHER_STARTED or not CFG.START_PROCESS then return end
  local cmd = (DIR .. 'content/KitGenerator/watcher.cmd'):gsub('/', '\\')
  local f = io.open(cmd, 'r')
  if not f then
    L('watcher not installed: run generator/setup_watcher.py to create ' .. cmd)
    return
  end
  f:close()
  WATCHER_STARTED = true
  local pid = get_pid()
  if pid then write_file('game.pid', tostring(pid)) end
  local res = run_winexec('cmd.exe /c "' .. cmd .. '"')
  L('kit watcher launched (pid ' .. tostring(pid) .. ', status ' .. tostring(res) .. ')')
end

local FRAME_COUNT = 0
function m.display_frame(ctx)
  if not WATCHER_STARTED and CFG.START_PROCESS and CFG.ENABLE_KITS then
    start_watcher()
  end
  install_undersleeve_hook(ctx)
  FRAME_COUNT = FRAME_COUNT + 1
  if (FRAME_COUNT % 30 == 0) or not STATE.date_ok then
    if is_in_ml(ctx) then
      detect_club(ctx)
      refresh_date(ctx)
    end
  end
end

-- ===== module init ========================================================
function m.init(ctx)
  DIR = tostring(ctx.sider_dir or '')
  if DIR ~= '' and DIR:sub(-1) ~= '\\' and DIR:sub(-1) ~= '/' then DIR = DIR .. '/' end
  load_offers()
  load_brands()
  load_club_file()
  load_deal()
  load_opted_in()
  load_paid()
  load_gdb_map()
  install_date_reader()
  install_undersleeve_hook(ctx)
  -- install_budget_hook and start_watcher deferred to display_frame / set_teams
  -- to guarantee game process and loader locks are fully initialized first
  refresh_date(ctx)
  local y, mo, d = game_date()
  if y then
    L(string.format('game date %04d-%02d-%02d -> season %d', y, mo, d, SEASON))
  else
    L('game date not readable yet (no career loaded?) - season default ' .. tostring(SEASON))
  end
  ensure_season_deal(SEASON)
  L(string.format('loaded v%s (kits %s, sponsorship %s, budget crediting %s)', m.version,
    CFG.ENABLE_KITS and 'ON' or 'OFF',
    CFG.ENABLE_SPONSORSHIP and 'ON' or 'OFF',
    (CFG.ENABLE_SPONSORSHIP and CFG.CREDIT_BUDGET) and 'ON' or 'OFF'))
  if CFG.ENABLE_SPONSORSHIP then
    if ctx.menu then
      ctx.menu.add({ id = 'sponsors', title = 'Sponsor Office', icon = 'tag', order = 30,
        description = 'ACTIVE SPONSORSHIP CONTRACT & MANAGEMENT  -  MODULE V2.1',
        status = function(c) return DEAL and 'Active' or 'Ready' end, build = build_office })
      ctx.register('key_down', m.key_down)
    else
      ctx.register('overlay_on', m.overlay_on)
      ctx.register('key_down', m.key_down)
    end
  end
  ctx.register('display_frame', m.display_frame)
  ctx.register('set_teams', m.set_teams)
  ctx.register('set_home_team_for_kits', m.set_home_team_for_kits)
  ctx.register('livecpk_make_key', m.make_key)
  ctx.register('livecpk_get_filepath', m.get_filepath)
end

-- small read-only accessor (diagnostics / tests)
function m.status()
  return { version = m.version, season = SEASON, year = STATE.year, month = STATE.month,
           day = STATE.day, date_ready = DATE.ready, mode = DATE.mode,
           budget_ready = BUDGET.ready, budget_disp = BUDGET.disp,
           budget_salary_disp = BUDGET.salary_disp,
           kits = CFG.ENABLE_KITS, sponsorship = CFG.ENABLE_SPONSORSHIP,
           club = club_id(), club_source = club_source(),
           club_name = club_id() and club_display_name(club_id()) or nil,
           club_matches = STATE.matches, brands = #BRANDS,
           deal = DEAL and DEAL.brand or nil,
           deal_bonus = DEAL and (DEAL.bonus or 0) or nil,
           deal_end = DEAL and deal_end() or nil }
end

-- diagnostic helper: credit an amount now (also handy as a manual fix-up).
-- NOTE: this is a raw credit and deliberately bypasses the per-season ledger.
function m.debug_credit(euros)
  return credit_budget(euros)
end

-- diagnostic helpers for the per-season payment guard (used by the tests)
function m.debug_set_deal(brand, club, season, value, years, bonus)
  DEAL = { id = 'debug', club = club, brand = brand, start = season,
           years = years or 1, value = value or 0, tier = 'mid', bonus = bonus or 0 }
  if club then OPTED_IN[club] = true end
  return true
end

function m.debug_clear_deal()
  DEAL = nil
  REQ_SEASONS = {}
  save_deal()
  return true
end

function m.debug_set_career(career_id)
  CAREER = career_id
  write_file('career.txt', CAREER .. '\n')
  reset_career_state()
  if load_deal then load_deal() end
  return true
end

function m.debug_set_opted_in(club, val)
  OPTED_IN[club] = (val ~= false)
  return true
end

function m.debug_clear_opted_in()
  OPTED_IN = {}
  write_file('opted_in.txt', '')
  return true
end

function m.debug_credit_now()
  credit_now()
  return SEL.credit_msg
end

function m.debug_is_paid(key)
  return PAID[key] == true
end

function m.debug_terminate()
  SEL.term_confirm = false
  terminate_deal()
  return SEL.credit_msg
end

function m.debug_should_queue_rollover(season, prev)
  return should_queue_rollover(season, prev)
end

-- Test hook: force the next make_key call to re-check watcher_state.txt for a
-- pending clean rebuild (normally throttled to once every 2 seconds).
function m.debug_reset_clean_check(club, season)
  local p = CLEAN_PENDING[club .. ':' .. season]
  if p then p.at = 0 end
  return p ~= nil
end

-- Set the calendar only (SEASON is left untouched) so refresh_date() can be
-- exercised with a real season transition in tests.
function m.debug_set_game_date(y, mo, d)
  STATE.year, STATE.month, STATE.day = y, mo, d
  STATE.date_ok = (y ~= nil)
  return true
end

-- diagnostic helpers for the managed-club auto-detection (used by the tests)
function m.debug_set_date(y, mo, d)
  STATE.year, STATE.month, STATE.day = y, mo, d
  STATE.date_ok = (y ~= nil)
  if y then
    SEASON = (mo >= 6) and (y + 1) or y
    ensure_season_deal(SEASON)
  end
  return SEASON
end

function m.debug_club_id()
  return club_id()
end

function m.debug_set_club(cid, persist)
  return set_club(cid, 'manual', persist ~= false)
end

function m.debug_clear_club()
  STATE.club, STATE.club_source, STATE.club_name = nil, nil, nil
  return true
end

function m.debug_reset_votes()
  STATE.votes, STATE.matches = {}, 0
  return true
end

function m.debug_record_match(home, away)
  record_match(home, away)
  return STATE.matches
end

function m.debug_learn_club()
  learn_club()
  return club_id()
end

function m.debug_visible_count()
  return #visible()
end

function m.debug_sign(brand, club, season, value, years, bonus)
  local o = { id = 'dbg-' .. tostring(brand) .. '-' .. tostring(season), club = club,
              brand = brand, season = season, years = years or 1, value = value or 0,
              bonus = bonus or 0, tier = 'mid', logo = path('logos/' .. tostring(brand) .. '.png') }
  sign_offer(o)
  return DEAL and DEAL.brand or nil
end

function m.debug_set_flag(name, value)
  CFG[name] = value
  return CFG[name]
end

function m.debug_reload_gdb_map()
  GDB_MAP_LOADED = false
  GDB_MAP = {}
  MAP_NAMES = nil
  load_gdb_map()
end

function m.debug_resolve_authentic_gdb_kit(tid, slot_type, slot, suffix)
  return resolve_authentic_gdb_kit(tid, slot_type, slot, suffix)
end

function m.debug_ensure_opponent_kits(opp_id)
  return ensure_opponent_kits(opp_id)
end

function m.debug_is_national_team(tid)
  return is_national_team(tid)
end

function m.debug_reset_jit_cache()
  JIT_REQUESTED = {}
  REQ_LEAGUE = {}
end

function m.debug_read_kit_meta(tid, slot_str)
  return read_kit_meta(tid, slot_str)
end

function m.debug_sync_undershirt(ctx, team_id, kit_id, cfg, is_gk)
  sync_undershirt_color(ctx, team_id, kit_id, cfg, is_gk)
end

function m.debug_install_undersleeve_hook(ctx)
  install_undersleeve_hook(ctx)
end

return m
