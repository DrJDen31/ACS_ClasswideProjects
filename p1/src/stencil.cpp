/*
1D 3-point Stencil Benchmark (Project #1)

- Computes for i in [1, N-2]: out[i] = a*x[i-1] + b*x[i] + c*x[i+1]
- Command-line options:
    --size N | -n N        number of elements (default: 1<<20)
    --reps R | -r R        repetitions for timing (default: 5)
    --misaligned           deliberately misalign output pointer to test unaligned stores
    --a A  --b B  --c C    stencil coefficients (defaults: A=0.5, B=1.0, C=0.5)
    --stride S | -s S      access stride (default: 1) applied to interior points
    --dtype D              runtime dtype: f32 or f64 (default: f32)
- Output: CSV header + one line with stats
    variant,n,reps,misaligned,median_ms,best_ms,gflops,max_abs_err
- FLOPs per interior element: 5 (3 mul + 2 add). GFLOP/s uses number of interior points visited.
- Vectorization variants provided by targets: stencil_scalar, stencil_auto, stencil_avx2
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
  float a = 0.5f, b = 1.0f, c = 0.5f;
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
    } else if (s == "--a") {
      args.a = std::stof(get(i));
    } else if (s == "--b") {
      args.b = std::stof(get(i));
    } else if (s == "--c") {
      args.c = std::stof(get(i));
    } else if (s == "--stride" || s == "-s") {
      args.stride = static_cast<size_t>(std::stoull(get(i)));
    } else if (s == "--dtype") {
      args.dtype = to_lower(std::string(get(i)));
      if (args.dtype != "f32" && args.dtype != "f64") {
        throw std::runtime_error("dtype must be f32 or f64");
      }
    } else if (s == "--help" || s == "-h") {
      std::cout << "Usage: stencil_[variant] --size N --reps R [--misaligned] [--a A --b B --c C] [--stride S] [--dtype f32|f64]\n";
      std::exit(0);
    }
  }
  return args;
}

template<typename T>
static void stencil_ref(T a, T b, T c, const T* x, T* y, size_t n, size_t stride) {
  if (n < 3) return;
  for (size_t i = 1; i + 1 < n; i += stride) {
    y[i] = a * x[i-1] + b * x[i] + c * x[i+1];
  }
}

template<typename T>
static void stencil_kernel(T a, T b, T c, const T* x, T* y, size_t n, size_t stride) {
  if (n < 3) return;
  for (size_t i = 1; i + 1 < n; i += stride) {
    y[i] = a * x[i-1] + b * x[i] + c * x[i+1];
  }
}

static double median(std::vector<double>& v) {
  if (v.empty()) return 0.0;
  std::nth_element(v.begin(), v.begin() + v.size()/2, v.end());
  return v[v.size()/2];
}

template<typename T>
int run_stencil_typed(const Args& args) {
  const size_t N = args.n;
  const size_t S = args.stride == 0 ? 1 : args.stride; // clamp
  const size_t bytes = N * sizeof(T);

  T* x = static_cast<T*>(aligned_alloc_bytes(64, bytes));
  T* y0 = static_cast<T*>(aligned_alloc_bytes(64, bytes));
  T* y  = static_cast<T*>(aligned_alloc_bytes(64, bytes + 64 + sizeof(T)));
  if (!x || !y0 || !y) throw std::bad_alloc();

  T* yout = y;
  if (args.misaligned) {
    yout = reinterpret_cast<T*>(reinterpret_cast<uintptr_t>(y) + sizeof(T));
  }

  std::mt19937 rng(99);
  std::uniform_real_distribution<double> dist(-1.0, 1.0);
  for (size_t i = 0; i < N; ++i) {
    x[i] = static_cast<T>(dist(rng));
    y0[i] = T(0);
    yout[i] = T(0);
  }

  stencil_ref<T>(static_cast<T>(args.a), static_cast<T>(args.b), static_cast<T>(args.c), x, y0, N, S);
  stencil_kernel<T>(static_cast<T>(args.a), static_cast<T>(args.b), static_cast<T>(args.c), x, yout, N, S);
  double max_abs_err = 0.0;
  for (size_t i = 0; i < N; ++i) max_abs_err = std::max(max_abs_err, std::abs(static_cast<double>(yout[i]) - static_cast<double>(y0[i])));

  stencil_kernel<T>(static_cast<T>(args.a), static_cast<T>(args.b), static_cast<T>(args.c), x, yout, N, S);

  std::vector<double> times_ms;
  times_ms.reserve(args.reps);

  for (int rep = 0; rep < args.reps; ++rep) {
    auto t0 = std::chrono::high_resolution_clock::now();
    stencil_kernel<T>(static_cast<T>(args.a), static_cast<T>(args.b), static_cast<T>(args.c), x, yout, N, S);
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    times_ms.push_back(ms);
  }

  double med_ms = median(times_ms);
  double best_ms = *std::min_element(times_ms.begin(), times_ms.end());
  double seconds = med_ms / 1e3;

  double effective = 0.0;
  if (N > 2) {
    effective = 1.0 + static_cast<double>((N - 3) / S);
  }
  double gflops = (5.0 * effective) / seconds / 1e9;

  std::string exe = "stencil";
  std::cout << "variant,n,reps,misaligned,median_ms,best_ms,gflops,max_abs_err\n";
  std::cout << exe << "," << N << "," << args.reps << "," << (args.misaligned?1:0) << ","
            << med_ms << "," << best_ms << "," << gflops << "," << max_abs_err << "\n";

  aligned_free(x);
  aligned_free(y0);
  aligned_free(y);
  return 0;
}

int main(int argc, char** argv) {
  try {
    Args args = parse_args(argc, argv);
    if (args.dtype == "f64") {
      return run_stencil_typed<double>(args);
    } else {
      return run_stencil_typed<float>(args);
    }
  } catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << "\n";
    return 1;
  }
}