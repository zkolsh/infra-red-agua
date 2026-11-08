CC := gcc
CFLAGS := -Wall -Wextra -std=c23 -ggdb -fsanitize=undefined,address -Iinclude
LDFLAGS := -lm

SRC_DIR := src
BUILD_DIR := build
LIB := libgraph_engine.so

SRCS := $(wildcard $(SRC_DIR)/*.c)
OBJS := $(patsubst $(SRC_DIR)/%.c,$(BUILD_DIR)/%.o,$(SRCS))
DEPS := $(OBJS:.o=.d)

.PHONY: all clean

all: $(LIB)

$(LIB): $(OBJS)
	$(CC) -shared $(CFLAGS) $^ -o $@ $(LDFLAGS)

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@

$(BUILD_DIR):
	mkdir -p $@

clean:
	rm -rf $(BUILD_DIR) $(LIB)

-include $(DEPS)
