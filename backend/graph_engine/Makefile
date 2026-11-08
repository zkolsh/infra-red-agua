CC := gcc
CFLAGS := -Wall -Wextra -std=c11 -Iinclude -fPIC -flto
LDFLAGS := -lm -flto

SRC_DIR := src
BUILD_DIR := build
LIB := libgraph_engine.so

SRCS := $(wildcard $(SRC_DIR)/*.c)
OBJS := $(patsubst $(SRC_DIR)/%.c,$(BUILD_DIR)/%.o,$(SRCS))
DEPS := $(OBJS:.o=.d)

.PHONY: all clean debug release

all: debug

debug: CFLAGS += -ggdb -fsanitize=address,undefined -DDEBUG
debug: LDFLAGS += -fsanitize=address,undefined
debug: $(LIB)

release: CFLAGS += -O2 -Werror -DNDEBUG
release: $(LIB)

$(LIB): $(OBJS)
	$(CC) -shared $(CFLAGS) $^ -o $@ $(LDFLAGS)

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@

$(BUILD_DIR):
	mkdir -p $@

clean:
	rm -rf $(BUILD_DIR) $(LIB)

-include $(DEPS)
