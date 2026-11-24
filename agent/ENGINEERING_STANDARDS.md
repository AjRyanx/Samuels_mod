# APEX ENGINEERING STANDARDS & PERFORMANCE PLAYBOOKS

> **Authoritative reference for efficient coding patterns, mechanical sympathy, clean architecture, and regression prevention across Python, C/C++, Lua, and Dart/Flutter.**

---

## Part 1: Core Architectural Principles (The "Palatable Speed" Mandate)

Performance without architecture is technical debt. APEX adheres strictly to these software development standards:

### 1. The Clean Encapsulation Rule
- **Standard:** Low-level, high-performance mechanisms (e.g. SIMD intrinsics, LuaJIT FFI, `mmap` buffers, pointer arithmetic, custom memory arenas) must **never** leak into business logic or public APIs.
- **Implementation:** Always wrap low-level optimizations behind a clean, idiomatic, type-safe public interface.
- **Fail-Safe Fallback:** Any platform- or hardware-specific acceleration (e.g. AVX2, NEON, OS-specific syscalls) must provide a clean, portable pure-language fallback path.

### 2. Documentation of Mechanical Intent
- **Standard:** Every optimization that deviates from standard idiomatic structure must include a concise docstring explaining the **mechanical cause**.
- **Example:**
  ```python
  # Optimized: Use pre-allocated bytearray with memoryview slicing.
  # Avoids allocating 12,000 intermediate bytes objects per tick,
  # keeping heap churn at zero and preserving L1 CPU cache locality.
  ```

### 3. The Amdahl's Law Threshold
- **Standard:** APEX never optimizes routines that contribute less than 15-20% of the profiled bottleneck unless the change also improves readability or simplifies architecture.
- **Anti-Pattern Rejected:** Spending days shaving 50 nanoseconds off a routine that runs once at application startup.

### 4. API Stability & Invariant Contracts
- **Standard:** Function signatures, return types, error handling, and behavioral invariants must remain identical before and after optimization.
- **Exception:** If breaking a signature is strictly required for zero-copy performance (e.g., passing a pre-allocated buffer instead of returning a new heap object), this must be introduced as an explicit, documented API alternative (e.g. `read_into(buf)` alongside `read()`).

---

## Part 2: Empirical Benchmarking & Statistical Rigor

APEX rejects "it feels faster." All claims require reproducible statistical evidence.

### 1. Benchmark Execution Methodology
1. **Warm-Up Runs:** Always execute warm-up passes ($N \ge 3$) to allow JIT compilers (LuaJIT, PyPy, Dart AOT/JIT) and OS disk caches to stabilize.
2. **Sample Size:** Micro-benchmarks require at least $N = 30$ iterations to compute valid statistical variance.
3. **Metrics Reported:**
   - **Wall-Clock Time:** Mean, Median, and Standard Deviation.
   - **Tail Latency:** P95 and P99 latency (critical for 60/120 FPS game loops and microservices).
   - **Memory Footprint:** Peak Resident Set Size (RSS) and Total Heap Allocations.
   - **Cache & CPU:** L1/L2 cache misses, branch mispredictions, context switches (where profilers permit).

### 2. Standard Profiling Tooling
- **CLI & Binary Latency:** `hyperfine --warmup 3 --runs 10`
- **Python:** `py-spy` (low-overhead sampling profiler), `cProfile`, `tracemalloc`, `memray`
- **C / C++:** `perf`, `valgrind --tool=callgrind`, Xcode Instruments, Clang Address/Memory Sanitizers
- **Lua / Sider:** Custom high-resolution tick counters (`os.clock()`, QueryPerformanceCounter), Lua memory hooks (`collectgarbage("count")`)
- **Dart & Flutter:** Flutter DevTools Timeline, CPU Profiler, Memory Allocation Tracker

---

## Part 3: Language & Runtime Performance Playbooks

---

### A. Python Systems & Developer Tooling

#### 1. Memory & Data Structure Standards
- **Use `__slots__` for High-Volume Objects:** Eliminates the per-instance `__dict__`, reducing object memory by up to 60% and speeding up attribute access.
- **Zero-Copy Slicing with `memoryview`:** When handling binary formats (e.g. PES `.ftex`, DDS textures, network buffers), slice with `memoryview` or `buffer` rather than string/bytes slicing to prevent heap copies.
- **Contiguous Arrays for Primitives:** Replace Python `list` of numbers with `array.array` or NumPy arrays to store contiguous unboxed C-types in memory.
- **String Interning:** Use `sys.intern()` for repeated string keys in large datasets to reduce equality checks from $O(N)$ string comparisons to $O(1)$ pointer comparisons.

#### 2. Loop & Algorithmic Optimizations
- **Local Variable Binding:** In tight loops, bind global and module-level lookups to local variables (`local_len = len`, `append = my_list.append`) to avoid dictionary lookups on each iteration.
- **Dictionary Lookups:** Use `dict.get()` or `key in dict` instead of `try...except KeyError` in hot loops where misses are frequent (exception handling is expensive in CPython).
- **Generator Pipelines vs Intermediate Lists:** Use generators for streaming transforms to keep peak memory at $O(1)$ instead of materializing full $O(N)$ lists.

#### 3. High-Speed Serialization & CLI Startup
- **Fast JSON/Binary:** Replace `json` with `orjson` (Rust-backed, 5-10x faster) or `msgpack`.
- **Deferred / Lazy Imports:** For CLI tools, defer heavy dependencies (e.g. `PIL`, `numpy`, `torch`, `scipy`) inside the specific subcommands that need them. This drops CLI cold startup time from ~800ms to <60ms.
- **Multiprocessing Over Threading for CPU Tasks:** Because of the Global Interpreter Lock (GIL), utilize `concurrent.futures.ProcessPoolExecutor` or `multiprocessing` for CPU-bound batch operations.

---

### B. C / C++ & Native Systems

#### 1. Cache-Conscious Memory Architecture
- **Data-Oriented Design (SoA vs AoS):**
  - *Bad (AoS):* Array of Structures causes cache pollution when iterating over a single attribute:
    ```cpp
    struct Entity { Vector3 pos; Matrix4 xform; Color color; int id; };
    Entity entities[10000]; // Iterating pos wastes cache loading xform/color/id
    ```
  - *Good (SoA):* Structure of Arrays packs hot fields contiguously in memory:
    ```cpp
    struct EntityGroup {
        alignas(64) float x[10000];
        alignas(64) float y[10000];
        alignas(64) float z[10000];
    };
    ```
- **False Sharing Prevention:** Align multithreaded shared data to 64-byte boundaries (`alignas(std::hardware_destructive_interference_size)`) so threads on different cores do not invalidate each other's L1 cache lines.

#### 2. Allocation & Pointer Efficiency
- **Zero Allocations on Hot Paths:** Pre-allocate static arenas, stack memory (`alloca` / `std::array`), or object pools. Never call `malloc`, `free`, `new`, or `delete` in real-time loops.
- **String & Span Views:** Replace `const std::string&` with `std::string_view` and array copies with `std::span` to pass non-owning references without heap allocations.
- **Smart Pointer Restraint:** Prefer raw non-owning references/pointers or `std::unique_ptr`. Avoid `std::shared_ptr` unless shared ownership is strictly required, as atomic reference counting introduces cache synchronization penalties.

#### 3. Modern Compiler & Hardware Utilization
- **Branch Prediction Hints:** Use `[[likely]]` and `[[unlikely]]` (C++20) on error paths to optimize instruction layout and prevent branch pipeline stalls.
- **Move Semantics:** Implement move constructors (`noexcept`) and use `std::move` to avoid deep copying buffers.
- **Optimization Flags:** Ensure production builds use `-O3`, `-flto` (Link-Time Optimization), and architecture-specific flags (e.g. `-march=native`).

---

### C. Lua & LuaJIT (Sider, Game Engines, Real-Time Hooks)

#### 1. The Zero-Allocation Game Loop Mandate
- **Real-Time Frame Budget:** In 60 FPS (16.6ms) or 120 FPS (8.3ms) game loops, **zero memory allocations** are permitted inside per-frame hooks (`overlay_on_frame`, `livecpk_make_key`).
- **Eliminate Table Churn:**
  - Never instantiate `{}` tables, closures, or formatted strings inside hooks.
  - Pre-allocate a static scratch table or buffer at module load time and overwrite its keys/indices.
  - Triggering Lua GC during gameplay causes micro-stutters and frame drops.

#### 2. Scope & Upvalue Caching
- **Localize All Global Functions:** Lua globals live in a hash table `_G`. Resolving `string.format` requires two hash lookups. Always localize at file scope:
  ```lua
  local string_format = string.format
  local string_sub    = string.sub
  local table_insert  = table.insert
  local math_floor    = math.floor
  ```

#### 3. LuaJIT FFI (Foreign Function Interface)
- **Direct Memory Access:** Use `ffi.cdef` to define C structures and access game engine memory pointers directly.
- **Avoid Table Conversions:** Do not translate C structs into Lua tables. Read and write directly to FFI cdata objects—LuaJIT compiles these into raw machine pointers with zero overhead.
- **Keep FFI Hot Loops JIT-Friendly:** Avoid calling `print`, `pairs()`, or throwing errors inside hot FFI loops, as these cause JIT compilation bailouts (NYI - Not Yet Implemented).

---

### D. Dart & Flutter UI & Application Performance

#### 1. Frame Budget & Widget Rebuild Minimization
- **Strict Budget:** Keep total UI work under **8.3ms (120 FPS)** or **16.6ms (60 FPS)** per frame.
- **`const` Constructor Propagation:** Always mark immutable widgets with `const`. Flutter short-circuits the `build()` tree for const widgets, eliminating re-instantiation entirely.
- **Push State to the Leaves:** Never call `setState()` at the root or page level. Isolate mutable state to small, dedicated leaf widgets or use targeted selectors (`select()` in Riverpod, `BlocSelector` in BLoC).

#### 2. Rendering & Paint Optimization
- **`RepaintBoundary` Placement:** Wrap complex, frequently animating widgets (e.g., custom spinners, progress bars, charts) in a `RepaintBoundary`. This separates their render layer from the rest of the screen, preventing cascading paint passes.
- **Avoid Expensive Canvas Calls:** Minimize `saveLayer()`, `BackdropFilter`, and complex opacity clipping (`Opacity` widget vs `Color.withOpacity`), as these force the GPU into offscreen render passes.
- **Avoid Layout Thrashing:** Never use `IntrinsicHeight` or `IntrinsicWidth` inside scrollable lists; they force an $O(N^2)$ double layout pass.

#### 3. Concurrency & Memory Hygiene
- **Offload Heavy Work to Isolates:** JSON decoding, image transformations, or heavy list processing must be sent to a background worker via `compute()` or worker `Isolate`s to prevent UI thread freezing.
- **Subscription & Controller Disposal:** Every `AnimationController`, `TextEditingController`, `ScrollController`, and `StreamSubscription` must be explicitly cancelled/disposed in `dispose()` to prevent permanent memory leaks.

---

## Part 4: The 6-Point Regression Prevention Protocol

Before applying any performance refactoring, APEX executes this protocol:

```
[ 1. MAP BLAST RADIUS ] ──> [ 2. TEST BASELINE ] ──> [ 3. BENCHMARK BASELINE ]
                                                              │
[ 6. PALATABILITY GATE ] <── [ 5. BENCHMARK DELTA ] <── [ 4. TEST VERIFICATION ]
```

1. **Map the Blast Radius:** Search every caller, consumer, and importer of the function/module being optimized.
2. **Test Baseline:** Run the existing test suite (`pytest`, `cargo test`, `ctest`, `flutter test`) to verify 100% green before editing a single line.
3. **Capture Baseline Telemetry:** Record wall-clock, memory, and allocation benchmarks under stable conditions.
4. **Test Verification:** Re-run all tests on the optimized code. Zero behavioral changes, zero regressions.
5. **Benchmark Delta Verification:** Run identical benchmark commands and verify measurable speedup/memory reduction.
6. **Palatability Gate:** Ensure the code is self-documenting, idiomatic, clean, and maintainable. If it looks like obfuscated spaghetti, refactor into clean abstractions.


---

## Part 5: Transformation Methods & Algorithmic Optimizations (The foo123 Catalog)

APEX applies structured, mathematical, and compiler-level transformations derived from classical optimization theory:

### 1. Loop Invariant Hoisting (Code Motion)
- **Rule:** Never recompute an invariant expression inside an iteration body.
- **Pattern:**
  ```python
  # Before: len(items) and base_factor * scale evaluated every iteration
  for item in items:
      process(item, base_factor * scale, len(items))

  # Optimized: Hoist invariant expressions outside the loop
  total_count = len(items)
  combined_factor = base_factor * scale
  for item in items:
      process(item, combined_factor, total_count)
  ```

### 2. Loop Unswitching
- **Rule:** If a loop contains a conditional branch that evaluates an invariant condition, move the condition outside the loop, creating two specialized loop branches. This eliminates branch prediction overhead inside the hot loop.
- **Pattern:**
  ```cpp
  // Before: Evaluating 'mode == Mode::Fast' on every iteration
  for (size_t i = 0; i < N; ++i) {
      if (mode == Mode::Fast) fast_op(data[i]);
      else standard_op(data[i]);
  }

  // Optimized: Branch hoisted outside the loop
  if (mode == Mode::Fast) {
      for (size_t i = 0; i < N; ++i) fast_op(data[i]);
  } else {
      for (size_t i = 0; i < N; ++i) standard_op(data[i]);
  }
  ```

### 3. Array Linearization (1D Spatial Contiguity)
- **Rule:** Flatten nested pointer graphs and multi-dimensional matrices `matrix[y][x]` into single contiguous 1D buffers `buffer[y * width + x]`.
- **Mechanical Win:** Multi-level pointer chasing (`**ptr`) suffers high L1/L2 cache miss rates. A linear 1D buffer activates hardware prefetchers, eliminates allocation fragmentation, and enables SIMD auto-vectorization.

### 4. Strength Reduction
- **Rule:** Replace computationally expensive operations with mathematically equivalent, lower-cost primitives:
  - Replace division/multiplication by powers of 2 with bitwise shifts (`x >> 1`, `x << 3`).
  - Replace modulo operations with bitwise AND for power-of-two divisors: `x % 16` $\to$ `x & 15`.
  - Replace repeated exponentiation (`pow(x, 2)`) with direct multiplication (`x * x`).
  - Replace costly square roots in distance comparisons (`sqrt(dx*dx + dy*dy) < R`) with squared distances (`dx*dx + dy*dy < R*R`).

### 5. Loop Fusion & Fission
- **Loop Fusion:** Combine adjacent loops iterating over the same range into a single loop, maximizing cache locality by keeping data in L1/L2 registers.
- **Loop Fission:** If a loop body is excessively large and spills hardware registers or overflows the L1 instruction cache, split it into two focused, cache-sized loops.

### 6. Common Subexpression Elimination (CSE) & Algebraic Reduction
- Factorize identical sub-calculations across expressions.
- Exploit mathematical symmetries, prefix sums, and Horner's method for polynomial evaluations to minimize total floating-point operations.
- Fast-path handling: Short-circuit trivial cases ($N=0, 1$, empty buffers, identity matrices) at the very top of function entry points.

---

## Part 6: Clean Code, Minimalism & Developer Ergonomics (The Gahlot Principles)

Optimizations that compromise developer productivity or codebase clarity are unacceptable. APEX strictly applies the software development standards established by Madhup Gahlot:

### 1. The Principle of Minimalism
- **Rule:** Less code means fewer bugs and lower cognitive load.
- **Action:** Eliminate duplicate, copy-pasted blocks with minor variations. Refactor shared mechanics into clean, cohesive primitives. Strive for concise, focused modules that do one job exceptionally well.

### 2. Consistency Beats Cleverness
- **Rule:** Predictable, readable code is infinitely superior to cryptic "clever" one-liners or esoteric hacks.
- **Action:** Reject obscure nested ternary chains, unreadable bitwise compression, or atypical language features unless encapsulated completely. Maintain consistent formatting, error-handling conventions, and design idioms across the codebase.

### 3. Intent-Driven Naming
- **Rule:** Names must communicate *intent* and *content* immediately without requiring mental translation.
- **Action:** Ban cryptic abbreviations and single-letter variables (e.g. `d`, `tmp`, `val`) outside of trivial loop counters (`i`, `j`). A variable must be named `uncompressed_texture_bytes`, not `utb`.

### 4. Comments Explain "Why", Not "What"
- **Rule:** Clean code describes *how* it operates; comments explain *why* specific architectural or mechanical choices were made.
- **Action:** Never write obvious comments like `# increments counter`. Write comments that document constraints, non-obvious business rules, or low-level runtime requirements:
  ```lua
  -- Pre-allocated static scratch table to ensure zero GC allocations during 60 FPS match gameplay
  local SCRATCH_BUFFER = {}
  ```

### 5. Problem Decomposition Before Coding
- **Rule:** Pause and outline the architecture before touching code.
- **Action:** Always plan the execution flow, map edge cases, verify invariants, and structure algorithms before writing implementation diffs.

---

## Part 7: Acceptance Gate Integrity (AGI) & Governed Promotion (The Writ Architecture)

Derived from Infinri Writ's governed execution architecture, APEX enforces **Acceptance Gate Integrity**: the agent proposes and performs work, but work cannot be promoted to "DONE" without passing hard, independently verified gates.

```
┌────────────────────────────────────────────────────────┐
│            AGI-1: ACTION AUTHORIZATION GATE            │
│  - Blast Radius Mapped                                 │
│  - Green Test Baseline Confirmed                       │
│  - Workload & Profiling Baseline Captured              │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               APEX OPTIMIZATION ENGINE                 │
│  - Amdahl's Law Hotpath Targeting                      │
│  - Foo123 Algorithmic & Memory Transformations         │
│  - Gahlot Clean Code & Minimalist Design               │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            AGI-2: ACCEPTANCE & PROMOTION GATE          │
│  - Gate A: 100% Tests Pass (Zero Regressions)         │
│  - Gate B: Independent Benchmark Confirms Speedup      │
│  - Gate C: Zero Memory Leaks / Headroom Maintained     │
│  - Gate D: Palatability & Ergonomics Review Passed     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            AGI-3: NO SELF-CERTIFICATION                │
│  - Proof must be generated by independent runners      │
│    (pytest, hyperfine, ctest, flutter test)            │
│  - Claims without terminal runner output are REJECTED  │
└────────────────────────────────────────────────────────┘
```

### 1. AGI-1: Action Authorization Gate
- No code modification may begin until:
  1. The blast radius of all consumers and importers has been identified.
  2. The existing test suite runs 100% green.
  3. A baseline performance metric is recorded under controlled conditions.

### 2. AGI-2: Acceptance & Promotion Gate
- A task can only transition to "COMPLETED" or "SHIPPED" if all 4 sub-gates pass:
  - **Correctness Gate:** 100% test pass rate on all existing and new invariant tests.
  - **Empirical Velocity Gate:** Measurable, statistically valid reduction in wall-clock time, CPU cycles, or memory.
  - **Resource Leak Gate:** Zero new memory leaks, unclosed streams, or retained heap allocations.
  - **Palatability Gate:** Code satisfies Gahlot's readability, intent-driven naming, and minimal complexity standards.

### 3. AGI-3: No Self-Certification
- APEX **cannot self-certify** completion by merely declaring "it works" or "the code is faster."
- All verification must be evidenced by invoking independent external tooling:
  - Test suites: `pytest`, `cargo test`, `flutter test`, `ctest`
  - Benchmarks: `hyperfine`, `py-spy`, `perf`, DevTools
- The exact execution commands and terminal outputs must be provided in the final report.

### 4. State Continuity & Provenance
- Maintain authoritative recovery state across development sessions:
  - Explicit record of what was changed and why.
  - Verifiable git diffs.
  - Documented benchmarks comparing identical input workloads.
