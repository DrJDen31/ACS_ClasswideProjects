CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O3 -march=native -pthread
SRC_DIR = ../src
INCLUDES = -I$(SRC_DIR)

# Source files
COARSE_SRC = $(SRC_DIR)/coarse_hash_table.cpp
FINE_SRC = $(SRC_DIR)/fine_hash_table.cpp
# RWLOCK_SRC = $(SRC_DIR)/rwlock_hash_table.cpp  # Uncomment when implemented
WORKLOAD_SRC = workloads.cpp

# Binary
BENCHMARK = benchmark

.PHONY: all clean

all: $(BENCHMARK)

$(BENCHMARK): benchmark.cpp $(WORKLOAD_SRC) $(COARSE_SRC) $(FINE_SRC)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $@ $^

clean:
	rm -f $(BENCHMARK)
	rm -rf ../results/raw/*.csv
