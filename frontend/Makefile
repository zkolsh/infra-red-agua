ELM := elm
SRC := src

SRCS := $(wildcard $(SRC_DIR)/*.elm)

.PHONY: all clean debug release dev

all: $(SRCS)
	elm make $(SRC)/Main.elm

# For parity against backend/

debug: all

release: all
	python3 -m http.server 8001

dev: all
	python3 -m http.server 8001

clean:
	rm -rf index.html elm-stuff/
