#define USE_GENERIC_ARENA

#if !defined(__linux) || defined(USE_GENERIC_ARENA)
// #if defined(DEBUG)
// #warning compiling generic arena implementation
// #else
// #error generic arena not allowed in release mode
// #endif

#include "arena.h"

#include <stdlib.h>
#include <string.h>

typedef struct arena_block_t arena_block_t;

struct arena_block_t {
	arena_block_t* next;
	void* memory;
};

struct arena_t {
	arena_block_t* blocks;
};

static void* allocate(arena_t* arena, size_t size, int zeroed) {
	if (!arena) {
		return NULL;
	};

	// avoid calling malloc(0)
	const size_t allocation_size = size? size : 1;
	void* memory = zeroed? calloc(1, allocation_size) : malloc(allocation_size);
	if (!memory) {
		return NULL;
	};

	arena_block_t* block = malloc(sizeof(*block));
	if (!block) {
		free(memory);
		return NULL;
	};

	block->memory = memory;
	block->next = arena->blocks;
	arena->blocks = block;
	return memory;
};

arena_t* arena_init(void) {
	arena_t* arena = malloc(sizeof(*arena));

	if (!arena) {
		return NULL;
	};

	arena->blocks = NULL;
	return arena;
};

void arena_deinit(arena_t* arena) {
	if (!arena) {
		return;
	};

	arena_block_t* block = arena->blocks;
	while (block) {
		arena_block_t* next = block->next;

		free(block->memory);
		free(block);

		block = next;
	};

	free(arena);
};

void* arena_alloc(arena_t* arena, size_t size) {
	return allocate(arena, size, 0);
};

void* arena_calloc(arena_t* arena, size_t size) {
	return allocate(arena, size, 1);
};

void* arena_realloc(arena_t* arena, void* ptr, size_t old_size, size_t new_size) {
	if (!arena) {
		return NULL;
	};

	if (!ptr) {
		return arena_alloc(arena, new_size);
	};

	if (!new_size) {
		return NULL;
	};

	void* memory = arena_alloc(arena, new_size);
	if (!memory) {
		return NULL;
	};

	size_t copy_size = old_size < new_size? old_size : new_size;
	memcpy(memory, ptr, copy_size);

	return memory;
};

#endif
