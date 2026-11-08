#if !defined(ARENA_H)
#define ARENA_H

#include <stddef.h>
#include <stdint.h>

typedef struct arena_t arena_t;

/* Creates and initializes an arena.  Returns NULL on failure. */
arena_t* arena_init(void);

/* Releases all arena memory and the arena itself.  Accepts NULL. */
void arena_deinit(arena_t* arena);

/* Allocates memory from the arena.  Allocations are aligned to max_align_t.
 * Returns NULL on failure.  Allocated memory is uninitialized. */
void* arena_alloc(arena_t* arena, size_t size);

/* Allocates memory from the arena.  Allocations are aligned to max_align_t.
 * Returns NULL on failure.  Allocated memory is zeroed. */
void* arena_calloc(arena_t* arena, size_t size);

/* Resizes an allocation.  Since individual allocations cannot be reclaimed,
 * the original allocation remains valid until arena_deinit().
 *
 * Existing contents are preserved up to min(old_size, new_size).
 * If ptr is NULL, behaves like arena_alloc().
 * If new_size is zero, returns NULL.
 *
 * Returns NULL on failure. The original allocation remains valid. */
void* arena_realloc(arena_t* arena, void* ptr, size_t old_size, size_t new_size);

#endif /* ARENA_H */

