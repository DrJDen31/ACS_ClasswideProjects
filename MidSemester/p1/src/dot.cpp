/*
Dot Product (Reduction) Benchmark

- Computes s = sum_i x[i] * y[i]
- Command-line options:
    --size N | -n N        number of elements (default: 1<<20)
    --reps R | -r R        repetitions for timing (default: 5)
    --misaligned           deliberately misalign y pointer to test unaligned loads
    --stride S | -s S      access stride (default: 1)
    --dtype D              runtime dtype: f32 or f64 (default: f32)
- Output: CSV header + one line with stats (variant, n, reps, misaligned, median_ms, best_ms, gflops, max_abs_err)
- FLOPs per updated element: 2 (mul + add). GFLOP/s computed on median time.
- Misalignment is implemented by offsetting the y pointer by sizeof(T) bytes to degrade 32/64B alignment while keeping type alignment.
- Vectorization variants are created at build time via different targets:
  dot_scalar (vectorization disabled), dot_auto (march=native), dot_avx2 (-mavx2 -mfma).
*/

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <numeric>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

#if defined(_MSC_VER)
  #include <malloc.h>
  static void* aligned_alloc_bytes(size_t alignment, size_t size) { return _aligned_malloc(size, alignment); }
  static void aligned_free(void* p) { _aligned_free(p); }
#else
  static void* aligned_alloc_bytes(size_t alignment, size_t size) {
    void* p = nullptr;
    if (posix_memalign(&p, alignment, size) != 0) return nullptr;
    return p;
  }
  static void aligned_free(void* p) { free(p); }
#endif

static std::string to_lower(std::string s) {
  std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c){ return std::tolower(c); });
  return s;
}

struct Args {
  size_t n = 1u << 20; // default 1M elements
  int reps = 5;
  bool misaligned = false;
  size_t stride = 1;
  std::string dtype = "f32";
};

static Args parse_args(int argc, char** argv) {
  Args args;
  for (int i = 1; i < argc; ++i) {
    std::string s(argv[i]);
    auto get = [&](int& i) -> const char* { if (i+1 >= argc) throw std::runtime_error("missing value for " + s); return argv[++i]; };
    if (s == "--size" || s == "-n") {
      args.n = static_cast<size_t>(std::stoull(get(i)));
    } else if (s == "--reps" || s == "-r") {
      args.reps = std::stoi(get(i));
    } else if (s == "--misaligned") {
      args.misaligned = true;
    } else if (s == "--stride" || s == "-s") {
      args.stride = static_cast<size_t>(std::stoull(get(i)));
    } else if (s == "--dtype") {
      args.dtype = to_lower(std::string(get(i)));
      if (args.dtype != "f32" && args.dtype != "f64") {
        throw std::runtime_error("dtype must be f32 or f64");
      }
    } else if (s == "--help" || s == "-h") {
      std::cout << "Usage: dot_[variant] --size N --reps R [--misaligned] [--stride S] [--dtype f32|f64]\n";
      std::exit(0);
    }
  }
  return args;
}

template<typename T>
static double dot_ref(const T* x, const T* y, size_t n, size_t stride) {
  double s = 0.0;
  for (size_t i = 0; i < n; i += stride) {
    s += static_cast<double>(x[i]) * static_cast<double>(y[i]);
  }
  return s;
}

template<typename T>
static T dot_kernel(const T* x, const T* y, size_t n, size_t stride) {
  T s = T(0);
  for (size_t i = 0; i < n; i += stride) {
    s += x[i] * y[i];
  }
  return s;
}

static double median(std::vector<double>& v) {
  if (v.empty()) return 0.0;
  std::nth_element(v.begin(), v.begin() + v.size()/2, v.end());
  return v[v.size()/2];
}

template<typename T>
int run_dot_typed(const Args& args) {
  const size_t N = args.n;
  const size_t S = args.stride == 0 ? 1 : args.stride; // clamp
  const size_t bytes = N * sizeof(T);

  T* x = static_cast<T*>(aligned_alloc_bytes(64, bytes));
  T* y0 = static_cast<T*>(aligned_alloc_bytes(64, bytes + 64 + sizeof(T)));
  if (!x || !y0) throw std::bad_alloc();

  T* y = y0;
  if (args.misaligned) {
    y = reinterpret_cast<T*>(reinterpret_cast<uintptr_t>(y0) + sizeof(T));
  }

  std::mt19937 rng(123);
  std::uniform_real_distribution<double> dist(-1.0, 1.0);
  for (size_t i = 0; i < N; ++i) {
    x[i] = static_cast<T>(dist(rng));
    y[i] = static_cast<T>(dist(rng));
  }

  double s_ref = dot_ref<T>(x, y, N, S);
  T s_out = dot_kernel<T>(x, y, N, S);
  double max_abs_err = std::abs(static_cast<double>(s_out) - s_ref);

  (void)dot_kernel<T>(x, y, N, S);

  std::vector<double> times_ms;
  times_ms.reserve(args.reps);

  for (int rep = 0; rep < args.reps; ++rep) {
    auto t0 = std::chrono::high_resolution_clock::now();
    volatile T s_tmp = dot_kernel<T>(x, y, N, S);
    (void)s_tmp;
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    times_ms.push_back(ms);
  }

  double med_ms = median(times_ms);
  double best_ms = *std::min_element(times_ms.begin(), times_ms.end());
  double seconds = med_ms / 1e3;
  size_t eff = ((N == 0) ? 0 : ((N - 1) / S) + 1);
  double gflops = (2.0 * static_cast<double>(eff)) / seconds / 1e9;

  std::string exe = "dot";
  std::cout << "variant,n,reps,misaligned,median_ms,best_ms,gflops,max_abs_err\n";
  std::cout << exe << "," << N << "," << args.reps << "," << (args.misaligned?1:0) << ","
            << med_ms << "," << best_ms << "," << gflops << "," << max_abs_err << "\n";

  aligned_free(x);
  aligned_free(y0);
  return 0;
}

int main(int argc, char** argv) {
  try {
    Args args = parse_args(argc, argv);
    if (args.dtype == "f64") {
      return run_dot_typed<double>(args);
    } else {
      return run_dot_typed<float>(args);
    }
  } catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << "\n";
    return 1;
  }
}