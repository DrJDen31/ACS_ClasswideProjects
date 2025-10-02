/*
SAXPY Benchmark (Project #1)

- computes y = a * x + y for a vector of length N.
- Purpose: quantify scalar vs SIMD performance across sizes, alignment, and ISA flags.
- Command-line options:
    --size N | -n N        number of elements (default: 1<<20)
    --reps R | -r R        repetitions for timing (default: 5)
    --misaligned           deliberately misalign y pointer (offset by sizeof(T))
    --alpha A | -a A       scalar multiplier a (default: 1.2345)
    --stride S | -s S      access stride (default: 1)
    --dtype D              runtime dtype: f32 or f64 (default: f32)
- Output CSV header:
    variant,n,reps,misaligned,median_ms,best_ms,gflops,max_abs_err
*/

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cctype>
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
  float a = 1.2345f;
  size_t stride = 1;   // access stride (elements)
  std::string dtype = "f32"; // runtime dtype: f32 or f64
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
    } else if (s == "--alpha" || s == "-a") {
      args.a = std::stof(get(i));
    } else if (s == "--dtype") {
      args.dtype = to_lower(std::string(get(i)));
      if (args.dtype != "f32" && args.dtype != "f64") {
        throw std::runtime_error("dtype must be f32 or f64");
      }
    } else if (s == "--help" || s == "-h") {
      std::cout << "Usage: saxpy_[variant] --size N --reps R [--misaligned] [--alpha A] [--stride S] [--dtype f32|f64]\n";
      std::exit(0);
    }
  }
  return args;
}

static double median(std::vector<double>& v) {
  if (v.empty()) return 0.0;
  std::nth_element(v.begin(), v.begin() + v.size()/2, v.end());
  return v[v.size()/2];
}

static std::string basename_prog(const char* prog) {
  if (!prog) return "saxpy";
  std::string p(prog);
  size_t pos_slash = p.find_last_of('/');
  size_t pos_bslash = p.find_last_of('\\');
  size_t pos = std::string::npos;
  if (pos_slash != std::string::npos && pos_bslash != std::string::npos) pos = std::max(pos_slash, pos_bslash);
  else if (pos_slash != std::string::npos) pos = pos_slash;
  else if (pos_bslash != std::string::npos) pos = pos_bslash;
  if (pos == std::string::npos) return p;
  return p.substr(pos + 1);
}

template<typename T>
static void saxpy_ref(double a64, const T* x, const T* y_in, T* y_out, size_t n, size_t stride) {
  std::memcpy(y_out, y_in, n * sizeof(T));
  const size_t S = (stride ? stride : 1);
  for (size_t idx = 0; idx < n; idx += S) {
    y_out[idx] = static_cast<T>(a64 * static_cast<double>(x[idx]) + static_cast<double>(y_in[idx]));
  }
}

template<typename T>
static void saxpy_kernel(T a, const T* x, T* y, size_t n, size_t stride) {
  const size_t S = (stride ? stride : 1);
  for (size_t idx = 0; idx < n; idx += S) {
    y[idx] = a * x[idx] + y[idx];
  }
}

template<typename T>
int run_saxpy_typed(const Args& args, const char* prog_name) {
  const size_t N = args.n;
  const size_t S = (args.stride == 0 ? 1 : args.stride);
  const size_t bytes = N * sizeof(T);

  T* x  = static_cast<T*>(aligned_alloc_bytes(64, bytes));
  T* y0 = static_cast<T*>(aligned_alloc_bytes(64, bytes));
  T* y  = static_cast<T*>(aligned_alloc_bytes(64, bytes + 64 + sizeof(T)));
  if (!x || !y0 || !y) throw std::bad_alloc();

  T* y_run = y;
  if (args.misaligned) {
    y_run = reinterpret_cast<T*>(reinterpret_cast<uintptr_t>(y) + sizeof(T));
  }

  std::mt19937 rng(42);
  std::uniform_real_distribution<double> dist(-1.0, 1.0);
  for (size_t i = 0; i < N; ++i) {
    x[i] = static_cast<T>(dist(rng));
    y0[i] = static_cast<T>(dist(rng));
    y_run[i] = y0[i];
  }

  std::vector<T> y_ref(N);
  saxpy_ref<T>(static_cast<double>(args.a), x, y0, y_ref.data(), N, S);
  saxpy_kernel<T>(static_cast<T>(args.a), x, y_run, N, S);
  double max_abs_err = 0.0;
  for (size_t i = 0; i < N; ++i) {
    max_abs_err = std::max(max_abs_err, std::abs(static_cast<double>(y_run[i]) - static_cast<double>(y_ref[i])));
  }

  std::memcpy(y_run, y0, bytes);

  // warmup
  saxpy_kernel<T>(static_cast<T>(args.a), x, y_run, N, S);
  std::memcpy(y_run, y0, bytes);

  std::vector<double> times_ms;
  times_ms.reserve(args.reps);

  for (int rep = 0; rep < args.reps; ++rep) {
    std::memcpy(y_run, y0, bytes);
    auto t0 = std::chrono::high_resolution_clock::now();
    saxpy_kernel<T>(static_cast<T>(args.a), x, y_run, N, S);
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    times_ms.push_back(ms);
  }

  double med_ms = median(times_ms);
  double best_ms = *std::min_element(times_ms.begin(), times_ms.end());
  double seconds = med_ms / 1e3;
  size_t eff = ((N == 0) ? 0 : ((N - 1) / S) + 1);
  double gflops = (2.0 * static_cast<double>(eff)) / seconds / 1e9;

  std::string exe = basename_prog(prog_name);
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
      return run_saxpy_typed<double>(args, argv[0]);
    } else {
      return run_saxpy_typed<float>(args, argv[0]);
    }
  } catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << "\n";
    return 1;
  }
}