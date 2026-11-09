#include "graph_engine.h"

#include "external/stb_ds.h"
#include "heap.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

#define NOT_FOUND SIZE_MAX
#define FLOW_EPS 1e-12

typedef struct {
	vertex_id_t key;
	size_t value;
} vertex_map_entry_t;

typedef struct {
	uint64_t key;
	size_t value;
} edge_map_entry_t;

struct graph_vertex_map_t {
	vertex_map_entry_t* entries;
	edge_map_entry_t* edge_entries;
};

static size_t find_vertex_index(const graph_t* g, vertex_id_t id) {
	if (!g || !g->vertex_map) {
		return NOT_FOUND;
	};

	ptrdiff_t index = hmgeti(g->vertex_map->entries, id);

	if (index < 0) {
		return NOT_FOUND;
	};

	return g->vertex_map->entries[index].value;
};

static uint64_t edge_key(vertex_id_t a, vertex_id_t b) {
	return a < b? ((uint64_t)a << 32) | b : ((uint64_t)b << 32) | a;
};

static size_t find_edge_index(const graph_t* g, vertex_id_t a, vertex_id_t b) {
	if (!g || !g->vertex_map) {
		return NOT_FOUND;
	};

	const uint64_t key = edge_key(a, b);
	const ptrdiff_t i = hmgeti(g->vertex_map->edge_entries, key);
	return i < 0? NOT_FOUND : g->vertex_map->edge_entries[i].value;
};

static bool valid_weight(double x) {
	return x >= 0.0 && !isnan(x);
};

static graph_status_t reserve_vertices(graph_t* g, size_t needed) {
	if (needed <= g->vertex_capacity) {
		return GRAPH_STATUS_OK;
	};

	size_t cap = g->vertex_capacity? g->vertex_capacity * 2 : 4;
	while (cap < needed) {
		cap *= 2;
	};

	vertex_t* p = arena_realloc(g->arena, g->vertices, g->vertex_capacity * sizeof(vertex_t), cap * sizeof(vertex_t));
	if (!p) {
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	g->vertices = p;
	g->vertex_capacity = cap;

	return GRAPH_STATUS_OK;
};

static graph_status_t reserve_edges(graph_t* g, size_t needed) {
	if (needed <= g->edge_capacity) {
		return GRAPH_STATUS_OK;
	};

	size_t cap = g->edge_capacity? g->edge_capacity * 2 : 4;
	while (cap < needed) {
		cap *= 2;
	};

	edge_t* p = arena_realloc(g->arena, g->edges, g->edge_capacity * sizeof(edge_t), cap * sizeof(edge_t));
	if (!p) {
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	g->edges = p;
	g->edge_capacity = cap;

	return GRAPH_STATUS_OK;
};

/* Union-find implementation with path compression */
typedef struct {
	size_t* parent;
	size_t* size;
} dsu_t;

static bool dsu_init(arena_t* arena, dsu_t* d, size_t n) {
	d->parent = arena_alloc(arena, n * sizeof(size_t));
	d->size = arena_alloc(arena, n * sizeof(size_t));
	if (!d->parent || !d->size) {
		return false;
	};

	for (size_t i = 0; i < n; i++) {
		d->parent[i] = i;
		d->size[i] = 1;
	};

	return true;
};

static size_t dsu_find(dsu_t* d, size_t x) {
	while (d->parent[x] != x) {
		d->parent[x] = d->parent[d->parent[x]];
		x = d->parent[x];
	};

	return x;
};

static bool dsu_union(dsu_t* d, size_t a, size_t b) {
	size_t ra = dsu_find(d, a);
	size_t rb = dsu_find(d, b);
	if (ra == rb) {
		return false;
	};

	if (d->size[ra] < d->size[rb]) {
		const size_t t = ra;
		ra = rb;
		rb = t;
	};

	d->parent[rb] = ra;
	d->size[ra] += d->size[rb];
	return true;
};

graph_t* graph_init_capacity(size_t vertex_capacity, size_t edge_capacity) {
	arena_t* a = arena_init();
	if (!a) {
		return NULL;
	};

	graph_t* g = arena_calloc(a, sizeof(graph_t));
	graph_vertex_map_t* map = g? arena_calloc(a, sizeof(*map)) : NULL;
	if (!g || !map) {
		arena_deinit(a);
		return NULL;
	};

	g->arena = a;
	g->vertex_map = map;

	if (vertex_capacity > 0) {
		g->vertices = arena_alloc(g->arena, vertex_capacity * sizeof(vertex_t));
		if (!g->vertices) {
			arena_deinit(a);
			return NULL;
		};

		g->vertex_capacity = vertex_capacity;
	};

	if (edge_capacity > 0) {
		g->edges = arena_alloc(g->arena, edge_capacity * sizeof(edge_t));
		if (!g->edges) {
			arena_deinit(a);
			return NULL;
		};

		g->edge_capacity = edge_capacity;
	};

	return g;
};

graph_t* graph_empty(void) {
	return graph_init_capacity(0, 0);
};

void graph_deinit(graph_t* graph) {
	if (!graph) {
		return;
	};

	if (graph->vertex_map) {
		hmfree(graph->vertex_map->entries);
		hmfree(graph->vertex_map->edge_entries);
	};

	arena_deinit(graph->arena);
};

graph_status_t graph_add_vertex(graph_t* graph, vertex_id_t id) {
	if (!graph) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	if (find_vertex_index(graph, id) != NOT_FOUND) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	graph_status_t s = reserve_vertices(graph, graph->vertex_count + 1);
	if (s != GRAPH_STATUS_OK) {
		return s;
	};

	const size_t index = graph->vertex_count++;
	graph->vertices[index].id = id;
	hmput(graph->vertex_map->entries, id, index);

	return GRAPH_STATUS_OK;
};

graph_status_t graph_add_edge(graph_t* graph, vertex_id_t source, vertex_id_t target, double construction_cost, double capacity) {
	if (!graph) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	if (!valid_weight(construction_cost) || !valid_weight(capacity)) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	if (source == target) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	if (find_vertex_index(graph, source) == NOT_FOUND || find_vertex_index(graph, target) == NOT_FOUND) {
		return GRAPH_STATUS_VERTEX_NOT_FOUND;
	};

	if (find_edge_index(graph, source, target) != NOT_FOUND) {
		return GRAPH_STATUS_EDGE_ALREADY_EXISTS;
	};

	const graph_status_t s = reserve_edges(graph, graph->edge_count + 1);
	if (s != GRAPH_STATUS_OK) {
		return s;
	};

	const size_t index = graph->edge_count++;
	edge_t* e = &graph->edges[index];
	e->source = source;
	e->target = target;
	e->construction_cost = construction_cost;
	e->capacity = capacity;

	const uint64_t key = edge_key(source, target);
	hmput(graph->vertex_map->edge_entries, key, index);
	return GRAPH_STATUS_OK;
};

graph_status_t graph_set_edge(graph_t* graph, vertex_id_t source, vertex_id_t target, double construction_cost, double capacity) {
	if (!graph) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	if (!valid_weight(construction_cost) || !valid_weight(capacity)) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	const size_t i = find_edge_index(graph, source, target);
	if (i == NOT_FOUND) {
		return GRAPH_STATUS_EDGE_NOT_FOUND;
	};

	graph->edges[i].construction_cost = construction_cost;
	graph->edges[i].capacity = capacity;
	return GRAPH_STATUS_OK;
};

graph_status_t graph_remove_edge(graph_t* graph, vertex_id_t source, vertex_id_t target) {
	if (!graph) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	const size_t i = find_edge_index(graph, source, target);
	if (i == NOT_FOUND) {
		return GRAPH_STATUS_EDGE_NOT_FOUND;
	};

	const uint64_t removed = edge_key(source, target);
	(void)hmdel(graph->vertex_map->edge_entries, removed);

	memmove(&graph->edges[i], &graph->edges[i + 1], (graph->edge_count - i - 1) * sizeof(edge_t));
	graph->edge_count--;

	for (size_t j = i; j < graph->edge_count; j++) {
		const uint64_t key = edge_key(graph->edges[j].source, graph->edges[j].target);
		hmput(graph->vertex_map->edge_entries, key, j);
	};

	return GRAPH_STATUS_OK;
};

size_t graph_get_vertex_count(const graph_t* graph) {
	return graph? graph->vertex_count : 0;
};

size_t graph_get_edge_count(const graph_t* graph) {
	return graph? graph->edge_count : 0;
};

graph_status_t graph_get_vertex_by_id(const graph_t* graph, vertex_id_t id, vertex_t* out_vertex) {
	if (!graph || !out_vertex) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	const size_t i = find_vertex_index(graph, id);
	if (i == NOT_FOUND) {
		return GRAPH_STATUS_VERTEX_NOT_FOUND;
	};

	*out_vertex = graph->vertices[i];

	return GRAPH_STATUS_OK;
};

graph_status_t graph_get_edge(const graph_t* graph, vertex_id_t source, vertex_id_t target, edge_t* out_edge) {
	if (!graph || !out_edge) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	const size_t i = find_edge_index(graph, source, target);
	if (i == NOT_FOUND) {
		return GRAPH_STATUS_EDGE_NOT_FOUND;
	};

	*out_edge = graph->edges[i];

	return GRAPH_STATUS_OK;
};

size_t graph_get_vertices(const graph_t* graph, vertex_t* out_vertices, size_t capacity) {
	if (!graph || !out_vertices) {
		return 0;
	};

	const size_t n = graph->vertex_count < capacity? graph->vertex_count : capacity;
	if (n) {
		memcpy(out_vertices, graph->vertices, n * sizeof(vertex_t));
	};

	return n;
};

size_t graph_get_edges(const graph_t* graph, edge_t* out_edges, size_t capacity) {
	if (!graph || !out_edges) {
		return 0;
	};

	const size_t n = graph->edge_count < capacity? graph->edge_count : capacity;
	if (n) {
		memcpy(out_edges, graph->edges, n * sizeof(edge_t));
	};

	return n;
};

graph_status_t graph_validate(const graph_t* g) {
	if (!g || !g->vertex_map) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	if (g->vertex_count > g->vertex_capacity || g->edge_count > g->edge_capacity) {
		return GRAPH_STATUS_INVALID_GRAPH;
	};

	if ((g->vertex_count && !g->vertices) || (g->edge_count && !g->edges)) {
		return GRAPH_STATUS_INVALID_GRAPH;
	};

	if ((size_t)hmlen(g->vertex_map->entries) != g->vertex_count || (size_t)hmlen(g->vertex_map->edge_entries) != g->edge_count) {
		return GRAPH_STATUS_INVALID_GRAPH; /* duplicates collapsed into one map entry */
	};

	for (size_t i = 0; i < g->vertex_count; i++) {
		if (find_vertex_index(g, g->vertices[i].id) != i) {
			return GRAPH_STATUS_INVALID_GRAPH;
		};
	};

	for (size_t i = 0; i < g->edge_count; i++) {
		const edge_t* e = &g->edges[i];
		if (e->source == e->target) {
			return GRAPH_STATUS_INVALID_GRAPH;
		};

		if (find_vertex_index(g, e->source) == NOT_FOUND || find_vertex_index(g, e->target) == NOT_FOUND) {
			return GRAPH_STATUS_INVALID_GRAPH;
		};

		if (!valid_weight(e->construction_cost) || !valid_weight(e->capacity)) {
			return GRAPH_STATUS_INVALID_GRAPH;
		};

		if (find_edge_index(g, e->source, e->target) != i) {
			return GRAPH_STATUS_INVALID_GRAPH;
		};
	};

	return GRAPH_STATUS_OK;
};

bool graph_is_connected(const graph_t* g) {
	if (!g) {
		return false;
	};

	const size_t n = g->vertex_count;
	if (n <= 1) {
		return true;
	};

	dsu_t dsu;
	if (!dsu_init(g->arena, &dsu, n)) {
		return false;
	};

	size_t components = n;
	for (size_t i = 0; i < g->edge_count && components > 1; i++) {
		if (dsu_union(&dsu, find_vertex_index(g, g->edges[i].source), find_vertex_index(g, g->edges[i].target))) {
			components--;
		};
	};

	return components == 1;
};

graph_status_t graph_subgraph_from_edges(const graph_t* original, const edge_t* edges, size_t edge_count, graph_t** out_graph) {
	if (!original || !out_graph || (edge_count && !edges)) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	graph_t* g = graph_init_capacity(original->vertex_count, edge_count);
	if (!g) {
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	/* Keep every vertex of the original graph. */
	if (original->vertex_count) {
		graph_status_t s = GRAPH_STATUS_OK;
		for (size_t i = 0; i < original->vertex_count && s == GRAPH_STATUS_OK; i++) {
			s = graph_add_vertex(g, original->vertices[i].id);
		};
	};

	g->vertex_count = original->vertex_count;

	for (size_t i = 0; i < edge_count; i++) {
		if (find_edge_index(original, edges[i].source, edges[i].target) == NOT_FOUND) {
			graph_deinit(g);
			return GRAPH_STATUS_EDGE_NOT_FOUND;
		};

		graph_status_t s = graph_add_edge(g, edges[i].source, edges[i].target, edges[i].construction_cost, edges[i].capacity);
		if (s != GRAPH_STATUS_OK) {
			graph_deinit(g);
			return s;
		};
	};

	*out_graph = g;
	return GRAPH_STATUS_OK;
};

/* Takes ownership of `edges` (may be NULL if count == 0). */
static graph_status_t make_mst_result(const edge_t* edges, size_t count, double total, mst_result_t** out) {
	mst_result_t* r = malloc(sizeof(*r));
	if (!r) {
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	edge_t* owned_edges = NULL;
	if (count) {
		owned_edges = malloc(count * sizeof(edge_t));

		if (!owned_edges) {
			free(r);
			return GRAPH_STATUS_OUT_OF_MEMORY;
		};

		memcpy(owned_edges, edges, count * sizeof(edge_t));
	};

	r->edges = owned_edges;
	r->edge_count = count;
	r->total_cost = total;

	*out = r;
	return GRAPH_STATUS_OK;
};

typedef struct {
	double cost;
	size_t a;
	size_t b;
	size_t edge_idx;
} resolved_edge_t;

static resolved_edge_t* resolve_edges(const graph_t* g, arena_t* arena) {
	resolved_edge_t* out = arena_alloc(arena, (g->edge_count? g->edge_count : 1) * sizeof(*out));
	if (!out) {
		return NULL;
	};

	for (size_t i = 0; i < g->edge_count; i++) {
		const edge_t* e = &g->edges[i];
		out[i] = (resolved_edge_t){
			.cost = e->construction_cost,
			.a = find_vertex_index(g, e->source),
			.b = find_vertex_index(g, e->target),
			.edge_idx = i
		};
	};

	return out;
};

static int compare_resolved(const void* x, const void* y) {
	const double a = ((const resolved_edge_t*)x)->cost, b = ((const resolved_edge_t*)y)->cost;
	return (a > b) - (a < b);
};

graph_status_t graph_kruskal(const graph_t* graph, mst_result_t** out_result) {
	if (!graph || !out_result) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	*out_result = NULL;
	const graph_status_t s = graph_validate(graph);
	if (s != GRAPH_STATUS_OK) {
		return s;
	};

	const size_t n = graph->vertex_count;
	if (n <= 1) {
		return make_mst_result(NULL, 0, 0.0, out_result);
	};

	resolved_edge_t* sorted = resolve_edges(graph, graph->arena);
	edge_t* chosen = arena_alloc(graph->arena, (n - 1) * sizeof(edge_t));
	dsu_t dsu;
	if (!sorted || !chosen || !dsu_init(graph->arena, &dsu, n)) {
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	qsort(sorted, graph->edge_count, sizeof(*sorted), compare_resolved);

	size_t count = 0;
	double total = 0.0;
	for (size_t i = 0; i < graph->edge_count && count < n - 1; i++) {
		if (dsu_union(&dsu, sorted[i].a, sorted[i].b)) {
			chosen[count++] = graph->edges[sorted[i].edge_idx];
			total += sorted[i].cost;
		};
	};

	return count == n - 1? make_mst_result(chosen, count, total, out_result) : GRAPH_STATUS_DISCONNECTED;
};

typedef struct {
	double cost;
	size_t to;
	size_t edge_idx;
} prim_node_t;

static enum Ordering prim_compare(const uint8_t* lhs, const uint8_t* rhs) {
	const double a = ((const prim_node_t*)lhs)->cost;
	const double b = ((const prim_node_t*)rhs)->cost;
	return a < b? LT : (a > b? GT : EQ);
};

graph_status_t graph_prim(const graph_t* graph, vertex_id_t source_id, mst_result_t** out_result) {
	if (!graph || !out_result) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	*out_result = NULL;
	const graph_status_t s = graph_validate(graph);
	if (s != GRAPH_STATUS_OK) {
		return s;
	};

	const size_t n = graph->vertex_count, m = graph->edge_count;
	if (n <= 1) {
		return make_mst_result(NULL, 0, 0.0, out_result);
	};

	const size_t start = find_vertex_index(graph, source_id);
	if (start == NOT_FOUND) {
		return GRAPH_STATUS_VERTEX_NOT_FOUND;
	};

	resolved_edge_t* ends = resolve_edges(graph, graph->arena);
	size_t* offset = arena_calloc(graph->arena, (n + 1) * sizeof(size_t));
	size_t* cursor = arena_alloc(graph->arena, n * sizeof(size_t));
	size_t* adj = arena_alloc(graph->arena, (2 * m + 1) * sizeof(size_t));
	edge_t* chosen = arena_alloc(graph->arena, (n - 1) * sizeof(edge_t));
	bool* in_tree = arena_calloc(graph->arena, n * sizeof(bool));
	if (!ends || !offset || !cursor || !adj || !chosen || !in_tree) {
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	for (size_t i = 0; i < m; i++) {
		offset[ends[i].a + 1]++;
		offset[ends[i].b + 1]++;
	};

	for (size_t v = 0; v < n; v++) {
		offset[v + 1] += offset[v];
	};

	memcpy(cursor, offset, n * sizeof(size_t));
	for (size_t i = 0; i < m; i++) {
		adj[cursor[ends[i].a]++] = i;
		adj[cursor[ends[i].b]++] = i;
	};

	Heap* heap = heap_init(sizeof(prim_node_t), prim_compare, LT);
	if (!heap) {
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	size_t count = 0, current = start;
	double total = 0.0;
	in_tree[start] = true;
	while (count < n - 1) {
		for (size_t k = offset[current]; k < offset[current + 1]; k++) {
			const resolved_edge_t* e = &ends[adj[k]];
			const size_t to = e->a == current? e->b : e->a;
			if (!in_tree[to]) {
				prim_node_t node = {.cost = e->cost, .to = to, .edge_idx = adj[k]};
				heap_insert(heap, (uint8_t*)&node);
			};
		};

		prim_node_t best;
		do {
			if (heap_is_empty(heap)) {
				heap_deinit(heap);
				return GRAPH_STATUS_DISCONNECTED;
			};

			heap_pop(heap, (uint8_t*)&best);
		} while (in_tree[best.to]);

		in_tree[best.to] = true;
		chosen[count++] = graph->edges[best.edge_idx];
		total += best.cost;
		current = best.to;
	};

	heap_deinit(heap);
	return make_mst_result(chosen, count, total, out_result);
};

double mst_get_total_cost(const mst_result_t* result) {
	return result? result->total_cost : 0.0;
};

size_t mst_get_edge_count(const mst_result_t* result) {
	return result? result->edge_count : 0;
};

size_t mst_get_edges(const mst_result_t* result, edge_t* out_edges, size_t capacity) {
	if (!result || !out_edges) {
		return 0;
	};

	const size_t n = result->edge_count < capacity? result->edge_count : capacity;
	if (n) {
		memcpy(out_edges, result->edges, n * sizeof(edge_t));
	};

	return n;
};

void mst_deinit(mst_result_t* result) {
	if (!result) {
		return;
	};
	
	free(result->edges);
	free(result);
};

/* Residual network using paired arcs: arc i and arc (i ^ 1) are reverses.
 *
 * Each physical (undirected) edge k becomes arcs 2k (source->target) and
 * 2k+1 (target->source), both with the edge capacity. Pushing f units on
 * one arc leaves cap = c - f there and c + f on its reverse, so the shared
 * capacity is respected and the net flow is c - cap[2k].
 *
 * Each demand vertex gets an arc to the artificial sink (capacity = demand)
 * with a zero-capacity reverse arc. */
typedef struct {
	size_t node_count;
	size_t arc_count;
	size_t* to;
	size_t* next;
	size_t* head;
	double* cap;
} residual_t;

static bool residual_init(arena_t* arena, residual_t* r, size_t nodes, size_t arcs) {
	r->node_count = nodes;
	r->arc_count = 0;

	r->to   = arena_alloc(arena, arcs  * sizeof(size_t));
	r->next = arena_alloc(arena, arcs  * sizeof(size_t));
	r->head = arena_alloc(arena, nodes * sizeof(size_t));
	r->cap  = arena_alloc(arena, arcs  * sizeof(double));

	if (!r->to || !r->next || !r->head || !r->cap) {
		return false;
	};

	for (size_t i = 0; i < nodes; i++) {
		r->head[i] = NOT_FOUND;
	};

	return true;
};

static void residual_add_arc(residual_t* r, size_t from, size_t to, double cap) {
	size_t i = r->arc_count++;
	r->to[i] = to;
	r->cap[i] = cap;
	r->next[i] = r->head[from];
	r->head[from] = i;
};

/* Searches for an augmenting path from s to t. bfs = true takes nodes from
 * the front of the work list (Edmonds-Karp); false takes from the back
 * (depth-first, Ford-Fulkerson). Returns the bottleneck, or 0 if no path. */
static double find_augmenting_path(residual_t* r, size_t s, size_t t, bool bfs, size_t* parent_arc, bool* visited, size_t* list) {
	if (!r) {
		return 0;
	};

	memset(visited, 0, r->node_count * sizeof(bool));
	size_t lo = 0, hi = 0;
	list[hi++] = s;
	visited[s] = true;

	while (lo < hi && !visited[t]) {
		size_t u = bfs? list[lo++] : list[--hi];

		for (size_t a = r->head[u]; a != NOT_FOUND; a = r->next[a]) {
			size_t v = r->to[a];

			if (!visited[v] && r->cap[a] > FLOW_EPS) {
				visited[v] = true;
				parent_arc[v] = a;
				list[hi++] = v;
			};
		};
	};

	if (!visited[t]) {
		return 0.0;
	};

	double bottleneck = INFINITY;
	for (size_t v = t; v != s; v = r->to[parent_arc[v] ^ 1]) {
		if (r->cap[parent_arc[v]] < bottleneck) {
			bottleneck = r->cap[parent_arc[v]];
		};
	};

	for (size_t v = t; v != s; v = r->to[parent_arc[v] ^ 1]) {
		r->cap[parent_arc[v]] -= bottleneck;
		r->cap[parent_arc[v] ^ 1] += bottleneck;
	};

	return bottleneck;
};

static graph_status_t flow_solve(const graph_t* graph, vertex_id_t source, const vertex_demand_t* demands, size_t demand_count, bool bfs, flow_result_t** out_result) {
	if (!graph || !out_result || (demand_count && !demands)) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	*out_result = NULL;

	const size_t n = graph->vertex_count;
	const size_t m = graph->edge_count;
	const size_t src = find_vertex_index(graph, source);
	if (src == NOT_FOUND) {
		return GRAPH_STATUS_VERTEX_NOT_FOUND;
	};

	arena_t* arena = arena_init();
	if (!arena) {
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	flow_result_t* res = NULL;
	edge_flow_t* edge_flows = NULL;
	vertex_flow_t* vertex_flows = NULL;

	graph_status_t status = GRAPH_STATUS_OK;
	if (m != n - 1 || !graph_is_connected(graph)) {
		free(edge_flows);
		free(vertex_flows);
		free(res);
		arena_deinit(arena);
		return GRAPH_STATUS_INVALID_GRAPH;
	};

	bool* seen = arena_calloc(arena, n * sizeof(bool));
	size_t* demand_vertex = arena_alloc(arena, (demand_count? demand_count : 1) * sizeof(size_t));
	if (!seen || !demand_vertex) {
		free(edge_flows);
		free(vertex_flows);
		free(res);
		arena_deinit(arena);
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	for (size_t i = 0; i < demand_count; i++) {
		if (!valid_weight(demands[i].demand) || demands[i].vertex_id == source) {
			free(edge_flows);
			free(vertex_flows);
			free(res);
			arena_deinit(arena);
			return GRAPH_STATUS_INVALID_ARGUMENT;
		};

		const size_t v = find_vertex_index(graph, demands[i].vertex_id);
		if (v == NOT_FOUND) {
			free(edge_flows);
			free(vertex_flows);
			free(res);
			arena_deinit(arena);
			return GRAPH_STATUS_VERTEX_NOT_FOUND;
		};

		if (seen[v]) {
			free(edge_flows);
			free(vertex_flows);
			free(res);
			arena_deinit(arena);
			return GRAPH_STATUS_INVALID_ARGUMENT;
		};

		seen[v] = true;
		demand_vertex[i] = v;
	};

	/* Residual network: node n is the artificial sink. */
	const size_t sink = n;
	residual_t r = {0};
	resolved_edge_t* ends = resolve_edges(graph, arena);
	if (!ends || !residual_init(arena, &r, n + 1, 2 * m + 2 * demand_count + 1)) {
		free(edge_flows);
		free(vertex_flows);
		free(res);
		arena_deinit(arena);
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	for (size_t k = 0; k < m; k++) {
		residual_add_arc(&r, ends[k].a, ends[k].b, graph->edges[k].capacity);
		residual_add_arc(&r, ends[k].b, ends[k].a, graph->edges[k].capacity);
	};

	const size_t sink_arc_base = r.arc_count;
	for (size_t i = 0; i < demand_count; i++) {
		residual_add_arc(&r, demand_vertex[i], sink, demands[i].demand);
		residual_add_arc(&r, sink, demand_vertex[i], 0.0);
	};

	size_t* parent_arc = arena_alloc(arena, (n + 1) * sizeof(size_t));
	bool* visited = arena_alloc(arena, (n + 1) * sizeof(bool));
	size_t* list = arena_alloc(arena, (n + 1) * sizeof(size_t));
	if (!parent_arc || !visited || !list) {
		free(edge_flows);
		free(vertex_flows);
		free(res);
		arena_deinit(arena);
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	while (find_augmenting_path(&r, src, sink, bfs, parent_arc, visited, list) > 0.0) {
		/* keep augmenting */
	};

	res = calloc(1, sizeof(*res));
	edge_flows = malloc((m? m : 1) * sizeof(edge_flow_t));
	vertex_flows = malloc((demand_count? demand_count : 1) * sizeof(vertex_flow_t));
	if (!res || !edge_flows || !vertex_flows) {
		free(edge_flows);
		free(vertex_flows);
		free(res);
		arena_deinit(arena);
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	for (size_t k = 0; k < m; k++) {
		const edge_t* e = &graph->edges[k];
		double flow = fabs(e->capacity - r.cap[2 * k]);
		if (flow > e->capacity) flow = e->capacity;

		edge_flows[k] = (edge_flow_t){
			.source = e->source, .target = e->target, .capacity = e->capacity, .flow = flow,
			.residual_capacity = e->capacity - flow,
			.utilization = e->capacity > 0.0? flow / e->capacity : 0.0,
			.saturated = (e->capacity - flow) <= FLOW_EPS,
		};
	};

	double total_flow = 0.0, total_demand = 0.0;
	for (size_t i = 0; i < demand_count; i++) {
		double delivered = demands[i].demand - r.cap[sink_arc_base + 2 * i];
		if (delivered < 0.0) {
			delivered = 0.0;
		};

		vertex_flows[i] = (vertex_flow_t){demands[i].vertex_id, demands[i].demand, delivered, demands[i].demand - delivered};
		total_flow += delivered;
		total_demand += demands[i].demand;
	};

	*res = (flow_result_t){total_flow, total_demand, edge_flows, m, vertex_flows, demand_count};
	*out_result = res;
	arena_deinit(arena);
	return status;
};

graph_status_t graph_ford_fulkerson(const graph_t* graph, vertex_id_t source, const vertex_demand_t* demand_vertices, size_t demand_count, flow_result_t** out_result) {
	return flow_solve(graph, source, demand_vertices, demand_count, false, out_result);
};

graph_status_t graph_edmonds_karp(const graph_t* graph, vertex_id_t source, const vertex_demand_t* demand_vertices, size_t demand_count, flow_result_t** out_result) {
	return flow_solve(graph, source, demand_vertices, demand_count, true, out_result);
};

double flow_get_total(const flow_result_t* result) {
	return result? result->total_flow : 0.0;
};

double flow_get_total_demand(const flow_result_t* result) {
	return result? result->total_demand : 0.0;
};

double flow_get_unmet_demand(const flow_result_t* result) {
	if (!result) return 0.0;
	const double unmet = result->total_demand - result->total_flow;
	return unmet > 0.0? unmet : 0.0;
};

bool flow_is_demand_satisfied(const flow_result_t* result) {
	return result && flow_get_unmet_demand(result) <= 1e-9;
};

size_t flow_get_edge_count(const flow_result_t* result) {
	return result ? result->edge_flow_count : 0;
};

size_t flow_get_edge_flows(const flow_result_t* result, edge_flow_t* out_flows, size_t capacity) {
	if (!result || !out_flows) {
		return 0;
	};

	const size_t n = result->edge_flow_count < capacity? result->edge_flow_count : capacity;
	if (n) {
		memcpy(out_flows, result->edge_flows, n * sizeof(edge_flow_t));
	};

	return n;
};

size_t flow_get_saturated_edge_count(const flow_result_t* result) {
	if (!result) {
		return 0;
	};

	size_t count = 0;
	for (size_t i = 0; i < result->edge_flow_count; i++) {
		if (result->edge_flows[i].saturated) {
			count++;
		};
	};

	return count;
};

size_t flow_get_saturated_edges(const flow_result_t* result, edge_flow_t* out_flows, size_t capacity) {
	if (!result || !out_flows) {
		return 0;
	};

	size_t count = 0;
	for (size_t i = 0; i < result->edge_flow_count && count < capacity; i++) {
		if (result->edge_flows[i].saturated) {
			out_flows[count++] = result->edge_flows[i];
		};
	};

	return count;
};

size_t flow_get_vertex_count(const flow_result_t* result) {
	return result? result->vertex_flow_count : 0;
};

size_t flow_get_vertex_flows(const flow_result_t* result, vertex_flow_t* out_flows, size_t capacity) {
	if (!result || !out_flows) {
		return 0;
	};

	const size_t n = result->vertex_flow_count < capacity? result->vertex_flow_count : capacity;
	if (n) {
		memcpy(out_flows, result->vertex_flows, n * sizeof(vertex_flow_t));
	};

	return n;
};

void flow_deinit(flow_result_t* result) {
	if (!result) {
		return;
	};

	free(result->edge_flows);
	free(result->vertex_flows);
	free(result);
};
