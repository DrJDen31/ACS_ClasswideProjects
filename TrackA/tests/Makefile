CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O3 -march=native -pthread
TSAN_FLAGS = -fsanitize=thread -g -O2
SRC_DIR = ../src
INCLUDES = -I$(SRC_DIR)

# Source files
COARSE_SRC = $(SRC_DIR)/coarse_hash_table.cpp
FINE_SRC = $(SRC_DIR)/fine_hash_table.cpp
# RWLOCK_SRC = $(SRC_DIR)/rwlock_hash_table.cpp  # Uncomment when implemented

# Test binaries
CORRECTNESS_TEST = test_correctness
STRESS_TEST = stress_test
TSAN_TEST = stress_test_tsan

.PHONY: all clean test

all: $(CORRECTNESS_TEST) $(STRESS_TEST)

$(CORRECTNESS_TEST): correctness_test.cpp $(COARSE_SRC) $(FINE_SRC)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $@ $^

$(STRESS_TEST): stress_test.cpp $(COARSE_SRC) $(FINE_SRC)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $@ $^

$(TSAN_TEST): stress_test.cpp $(COARSE_SRC) $(FINE_SRC)
	$(CXX) $(TSAN_FLAGS) $(INCLUDES) -o $@ $^

test: $(CORRECTNESS_TEST) $(STRESS_TEST)
	@echo "Running correctness tests..."
	./$(CORRECTNESS_TEST)
	@echo "Running stress tests..."
	./$(STRESS_TEST) 8

tsan: $(TSAN_TEST)
	@echo "Running ThreadSanitizer stress test..."
	./$(TSAN_TEST) 16

clean:
	rm -f $(CORRECTNESS_TEST) $(STRESS_TEST) $(TSAN_TEST)
