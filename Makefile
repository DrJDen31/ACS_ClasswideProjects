# Makefile for B2 Tier-Aware ANN Search Project

CXX := g++
CXXFLAGS := -std=c++17 -O3 -march=native -Wall -Wextra -pthread
INCLUDES := -Isrc
LDFLAGS := -pthread

# Directories
SRC_DIR := src
TEST_DIR := tests
BENCH_DIR := benchmarks
BUILD_DIR := build
BIN_DIR := bin

# Source files (to be expanded as implementation progresses)
CORE_SRCS := $(wildcard $(SRC_DIR)/core/*.cpp)
ANN_SRCS := $(wildcard $(SRC_DIR)/ann/*.cpp)
STORAGE_SRCS := $(wildcard $(SRC_DIR)/storage/*.cpp)
TIERED_SRCS := $(wildcard $(SRC_DIR)/tiered/*.cpp)
SIMULATOR_SRCS := $(wildcard $(SRC_DIR)/simulator/*.cpp)
UTILS_SRCS := $(wildcard $(SRC_DIR)/utils/*.cpp)

ALL_SRCS := $(CORE_SRCS) $(ANN_SRCS) $(STORAGE_SRCS) $(TIERED_SRCS) $(SIMULATOR_SRCS) $(UTILS_SRCS)
ALL_OBJS := $(patsubst $(SRC_DIR)/%.cpp,$(BUILD_DIR)/%.o,$(ALL_SRCS))

# Test files
UNIT_TESTS := $(wildcard $(TEST_DIR)/unit/*.cpp)
INTEGRATION_TESTS := $(wildcard $(TEST_DIR)/integration/*.cpp)
TEST_BINS := $(patsubst $(TEST_DIR)/%.cpp,$(BIN_DIR)/test_%,$(UNIT_TESTS) $(INTEGRATION_TESTS))

# Benchmark files
BENCH_SRCS := $(wildcard $(BENCH_DIR)/*.cpp)
BENCH_BINS := $(patsubst $(BENCH_DIR)/%.cpp,$(BIN_DIR)/%,$(BENCH_SRCS))

.PHONY: all clean test benchmarks dirs

all: dirs $(ALL_OBJS)

dirs:
	@mkdir -p $(BUILD_DIR)/core $(BUILD_DIR)/ann $(BUILD_DIR)/storage $(BUILD_DIR)/tiered $(BUILD_DIR)/simulator $(BUILD_DIR)/utils
	@mkdir -p $(BIN_DIR)
	@mkdir -p $(BIN_DIR)/test_unit $(BIN_DIR)/test_integration

# Compile source files to object files
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

# Build test executables and run them as a suite (when test files exist)
test: dirs $(ALL_OBJS) $(TEST_BINS)
	@echo "Building and running unit/integration tests..."
	@for t in $(TEST_BINS); do \
		echo "Running $$t"; \
		"./$$t" || exit 1; \
	done

$(BIN_DIR)/test_%: $(TEST_DIR)/%.cpp $(ALL_OBJS)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< $(ALL_OBJS) -o $@ $(LDFLAGS)

# Build benchmark executables (when benchmark files exist)
benchmarks: dirs $(ALL_OBJS) $(BENCH_BINS)
	@echo "Building benchmark binaries in $(BIN_DIR)..."

$(BIN_DIR)/%: $(BENCH_DIR)/%.cpp $(ALL_OBJS)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< $(ALL_OBJS) -o $@ $(LDFLAGS)

clean:
	rm -rf $(BUILD_DIR) $(BIN_DIR)

# Development targets
format:
	find $(SRC_DIR) $(TEST_DIR) -name "*.hpp" -o -name "*.cpp" | xargs clang-format -i

lint:
	cppcheck --enable=all --inconclusive --std=c++17 $(SRC_DIR)
