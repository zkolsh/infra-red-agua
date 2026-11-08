#define HEAP_EXPOSE_INTERNAL
#include "heap.h"

#define HEAP_AT(heap, i) ((heap)->data + (i) * (heap)->stride)

Heap* heap_init(const size_t stride, Comparison compare, const enum Ordering order) {
	arena_t* arena = arena_init();
	if (!arena) {
		return NULL;
	};

	Heap* heap = arena_alloc(arena, sizeof(Heap));
	if (!heap) {
		arena_deinit(arena);
		return NULL;
	};

	heap->capacity = HEAP_MINIMUM_CAPACITY;
	heap->size = 0;
	heap->stride = stride;
	heap->arena = arena;
	heap->compare = compare;
	heap->data = arena_alloc(heap->arena, stride * heap->capacity);
	heap->order = order;

	if (!heap->data) {
		arena_deinit(arena);
		return NULL;
	};

	return heap;
};

bool heap_is_empty(const Heap* heap) {
	if (!heap) {
		return true;
	};

	return heap->size == 0;
};

size_t heap_size(const Heap* heap) {
	if (!heap) {
		return 0;
	};

	return heap->size;
};

void heap_deinit(Heap* heap) {
	if (heap == NULL) {
		return;
	};
	
	arena_deinit(heap->arena);
};

bool heap_realloc(Heap* heap, size_t new_capacity) {
	uint8_t* new_data = arena_realloc(heap->arena, heap->data, heap->capacity * heap->stride, new_capacity * heap->stride);
	if (new_data == NULL) {
		heap_deinit(heap);
		return false;
	};

	heap->data = new_data;
	heap->capacity = new_capacity;
	return true;
};

uint8_t* heap_top(const Heap* heap) {
	if (!heap || !heap->size || !heap->data) {
		return NULL;
	};

	return (uint8_t*)HEAP_AT(heap, 1);
};

void heap_insert(Heap* heap, uint8_t* data) {
	if (!heap) {
		return;
	};

	if (heap->capacity < HEAP_MINIMUM_CAPACITY) {
		heap_realloc(heap, HEAP_MINIMUM_CAPACITY);
	};

	if (heap->size == 0) {
		memcpy(HEAP_AT(heap, 1), data, heap->stride);
		heap->size = 1;
		return;
	};

	while (heap->size + 1 > heap->capacity) {
		heap_realloc(heap, heap->capacity * 2);
	};

	heap->size++;
	memcpy(HEAP_AT(heap, heap->size), data, heap->stride);

	uint8_t* aux = heap->data;
	size_t index = heap->size;
	assert(aux);

	const enum Ordering disordered = (heap->order == GT)? LT : GT;
	while (index > 1) {
		size_t parent = index / 2;

		if (heap->compare(HEAP_AT(heap, parent), HEAP_AT(heap, index)) == disordered) {
			memcpy(aux, HEAP_AT(heap, parent), heap->stride);
			memcpy(HEAP_AT(heap, parent), HEAP_AT(heap, index), heap->stride);
			memcpy(HEAP_AT(heap, index), aux, heap->stride);
			index = parent;
		} else {
			break;
		}
	};
};

void heap_pop(Heap* heap, uint8_t* out_data) {
	if (!heap || !heap->size) {
		return;
	};

	if (out_data) {
		memcpy(out_data, HEAP_AT(heap, 1), heap->stride);
	};

	memcpy(HEAP_AT(heap, 1), HEAP_AT(heap, heap->size), heap->stride);
	heap->size--;

	size_t index = 1;
	const enum Ordering disordered = (heap->order == GT) ? LT : GT;

	while (2 * index <= heap->size) {
		size_t left = 2 * index;
		size_t right = 2 * index + 1;
		size_t next = left;

		if (right <= heap->size) {
			const enum Ordering rel = heap->compare(HEAP_AT(heap, left), HEAP_AT(heap, right));
			next = (rel == heap->order) ? left : right;
		};

		if (heap->compare(HEAP_AT(heap, index), HEAP_AT(heap, next)) == disordered) {
			memcpy(heap->data, HEAP_AT(heap, index), heap->stride);
			memcpy(HEAP_AT(heap, index), HEAP_AT(heap, next), heap->stride);
			memcpy(HEAP_AT(heap, next), heap->data, heap->stride);
			index = next;
		} else {
			break;
		};
	};
};
