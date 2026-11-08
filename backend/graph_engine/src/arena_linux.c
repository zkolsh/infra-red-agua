#if defined(__linux__) && !defined(USE_GENERIC_ARENA)
#include "arena.h"

#define _GNU_SOURCE
#include <sys/mman.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <stdalign.h>
#include <stdint.h>

/* Default virtual capacity per chunk: 1 GB. 
 * Virtual memory is cheap and uncommitted until touched.
 * If we need more than 1GB for a request, we're screwed anyways. */
#if !defined(ARENA_DEFAULT_CAPACITY)
#define ARENA_DEFAULT_CAPACITY (1ull << 30)
#endif

typedef struct arena_chunk_t arena_chunk_t;

struct arena_chunk_t {
	void* base;
	size_t capacity;
	size_t offset;
	arena_chunk_t* next;
};

struct arena_t {
	arena_chunk_t* current;
	arena_chunk_t* head;
};

static size_t align_forward(size_t ptr, size_t alignment) {
	const size_t modulo = ptr & (alignment - 1);
	if (modulo != 0) {
		ptr += (alignment - modulo);
	};

	return ptr;
};

static arena_chunk_t* arena_chunk_create(size_t min_capacity) {
	long page_size = sysconf(_SC_PAGESIZE);
	if (page_size < 0) page_size = 4096;

	size_t capacity = ARENA_DEFAULT_CAPACITY;
	if (min_capacity > capacity) {
		capacity = min_capacity;
	};

	capacity = (capacity + page_size - 1) & ~(page_size - 1);

	void* base = mmap(NULL, capacity, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (base == MAP_FAILED) {
		return NULL;
	};

	arena_chunk_t* chunk = malloc(sizeof(*chunk));
	if (!chunk) {
		munmap(base, capacity);
		return NULL;
	};

	chunk->base = base;
	chunk->capacity = capacity;
	chunk->offset = 0;
	chunk->next = NULL;
	return chunk;
};

arena_t* arena_init(void) {
	arena_t* arena = malloc(sizeof(*arena));
	if (!arena) {
		return NULL;
	};

	arena_chunk_t* chunk = arena_chunk_create(ARENA_DEFAULT_CAPACITY);
	if (!chunk) {
		free(arena);
		return NULL;
	};

	arena->head = chunk;
	arena->current = chunk;
	return arena;
};

void arena_deinit(arena_t* arena) {
	if (!arena) {
		return;
	};

	arena_chunk_t* chunk = arena->head;
	while (chunk) {
		arena_chunk_t* next = chunk->next;
		munmap(chunk->base, chunk->capacity);
		free(chunk);
		chunk = next;
	};

	free(arena);
};

static void* allocate(arena_t* arena, size_t size, int zeroed) {
	if (!arena) {
		return NULL;
	};

	const size_t alloc_size = size? size : 1;
	const size_t alignment = alignof(max_align_t);

	arena_chunk_t* chunk = arena->current;
	size_t current_addr = (size_t)((char*)chunk->base + chunk->offset);
	size_t aligned_addr = align_forward(current_addr, alignment);
	size_t padding = aligned_addr - current_addr;
	size_t total_size = alloc_size + padding;
	if (chunk->offset + total_size > chunk->capacity) {
		arena_chunk_t* new_chunk = arena_chunk_create(total_size);
		if (!new_chunk) {
			return NULL;
		};

		chunk->next = new_chunk;
		arena->current = new_chunk;
		chunk = new_chunk;

		current_addr = (size_t)chunk->base;
		aligned_addr = align_forward(current_addr, alignment);
		padding = aligned_addr - current_addr;
		total_size = alloc_size + padding;
	};

	void* memory = (void*)aligned_addr;
	chunk->offset += total_size;

	if (zeroed) {
		memset(memory, 0, alloc_size);
	};

	return memory;
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

	const size_t copy_size = old_size < new_size? old_size : new_size;
	memcpy(memory, ptr, copy_size);

	return memory;
};

#endif
