#if !defined(HEAP_H)
#define HEAP_H

#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#if !defined(HEAP_MINIMUM_CAPACITY)
#define HEAP_MINIMUM_CAPACITY 64
#endif //HEAP_MINIMUM_CAPACITY

enum Ordering: uint8_t {
	LT = -1,
	EQ = 0,
	GT = 1
};

typedef enum Ordering(*Comparison)(const uint8_t* lhs, const uint8_t* rhs);

#if !defined(HEAP_EXPOSE_INTERNAL)
typedef struct Heap Heap;
#else
#include "arena.h"

typedef struct Heap {
	size_t capacity;
	size_t size;
	size_t stride;
	arena_t* arena;
	Comparison compare;
	enum Ordering order;
	uint8_t* data;
} Heap;
#endif //HEAP_EXPOSE_INTERNAL

Heap* heap_init(const size_t stride, Comparison compare, const enum Ordering order);
bool heap_is_empty(const Heap* heap);
size_t heap_size(const Heap* heap);
void heap_deinit(Heap* heap);
bool heap_realloc(Heap* heap, size_t new_capacity);
uint8_t* heap_top(const Heap* heap);
void heap_insert(Heap* heap, uint8_t* data);
void heap_pop(Heap* heap, uint8_t* out_data);

#endif /* HEAP_H */
