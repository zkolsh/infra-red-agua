#include "graph_engine.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

#define NOT_FOUND SIZE_MAX
#define FLOW_EPS 1e-12

static size_t find_vertex_index(const graph_t* g, vertex_id_t id) {
	for (size_t i = 0; i < g->vertex_count; i++) {
		if (g->vertices[i].id == id) return i;
	};

	return NOT_FOUND;
};

static size_t find_edge_index(const graph_t* g, vertex_id_t a, vertex_id_t b) {
	for (size_t i = 0; i < g->edge_count; i++) {
		const edge_t* e = &g->edges[i];
		if ((e->source == a && e->target == b) || (e->source == b && e->target == a)) return i;
	};
	return NOT_FOUND;
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

	vertex_t* p = realloc(g->vertices, cap * sizeof(vertex_t));
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

	edge_t* p = realloc(g->edges, cap * sizeof(edge_t));
	if (!p) {
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	g->edges = p;
	g->edge_capacity = cap;

	return GRAPH_STATUS_OK;
};

/* Union-find implementation (does path compression) */
static size_t dsu_find(size_t* parent, size_t x) {
	while (parent[x] != x) {
		parent[x] = parent[parent[x]];
		x = parent[x];
	};

	return x;
};

static bool dsu_union(size_t* parent, size_t a, size_t b) {
	const size_t ra = dsu_find(parent, a);
	const size_t rb = dsu_find(parent, b);
	if (ra == rb) {
		return false;
	};

	parent[ra] = rb;
	return true;
};

graph_t* graph_init_capacity(size_t vertex_capacity, size_t edge_capacity) {
	graph_t* g = calloc(1, sizeof(graph_t));
	if (!g) {
		return NULL;
	};

	if (vertex_capacity > 0) {
		g->vertices = malloc(vertex_capacity * sizeof(vertex_t));
		if (!g->vertices) {
			free(g);
			return NULL;
		};

		g->vertex_capacity = vertex_capacity;
	};

	if (edge_capacity > 0) {
		g->edges = malloc(edge_capacity * sizeof(edge_t));
		if (!g->edges) {
			free(g->vertices);
			free(g);
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

	free(graph->vertices);
	free(graph->edges);
	free(graph);
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

	graph->vertices[graph->vertex_count++].id = id;

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

	graph_status_t s = reserve_edges(graph, graph->edge_count + 1);
	if (s != GRAPH_STATUS_OK) {
		return s;
	};

	edge_t* e = &graph->edges[graph->edge_count++];
	e->source = source;
	e->target = target;
	e->construction_cost = construction_cost;
	e->capacity = capacity;

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

	memmove(&graph->edges[i], &graph->edges[i + 1], (graph->edge_count - i - 1) * sizeof(edge_t));
	graph->edge_count--;

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

graph_status_t graph_validate(const graph_t* graph) {
	if (!graph) return GRAPH_STATUS_INVALID_ARGUMENT;
	if (graph->vertex_count > graph->vertex_capacity || graph->edge_count > graph->edge_capacity)
		return GRAPH_STATUS_INVALID_GRAPH;
	if ((graph->vertex_count && !graph->vertices) || (graph->edge_count && !graph->edges))
		return GRAPH_STATUS_INVALID_GRAPH;

	for (size_t i = 0; i < graph->vertex_count; i++)
		for (size_t j = i + 1; j < graph->vertex_count; j++)
			if (graph->vertices[i].id == graph->vertices[j].id) return GRAPH_STATUS_INVALID_GRAPH;

	for (size_t i = 0; i < graph->edge_count; i++) {
		const edge_t* e = &graph->edges[i];
		if (find_vertex_index(graph, e->source) == NOT_FOUND || find_vertex_index(graph, e->target) == NOT_FOUND)
			return GRAPH_STATUS_INVALID_GRAPH;
		if (e->source == e->target) return GRAPH_STATUS_INVALID_GRAPH;
		if (!valid_weight(e->construction_cost) || !valid_weight(e->capacity)) return GRAPH_STATUS_INVALID_GRAPH;
		for (size_t j = i + 1; j < graph->edge_count; j++) {
			const edge_t* f = &graph->edges[j];
			if ((e->source == f->source && e->target == f->target) ||
					(e->source == f->target && e->target == f->source))
				return GRAPH_STATUS_INVALID_GRAPH;
		}
	}
	return GRAPH_STATUS_OK;
}

bool graph_is_connected(const graph_t* graph) {
	if (!graph || graph_validate(graph) != GRAPH_STATUS_OK) return false;
	size_t n = graph->vertex_count;
	if (n <= 1) return true;

	size_t* parent = malloc(n * sizeof(size_t));
	if (!parent) return false;
	for (size_t i = 0; i < n; i++) parent[i] = i;

	size_t components = n;
	for (size_t i = 0; i < graph->edge_count; i++) {
		size_t a = find_vertex_index(graph, graph->edges[i].source);
		size_t b = find_vertex_index(graph, graph->edges[i].target);
		if (dsu_union(parent, a, b)) components--;
	}
	free(parent);
	return components == 1;
}

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
		memcpy(g->vertices, original->vertices, original->vertex_count * sizeof(vertex_t));
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
static graph_status_t make_mst_result(edge_t* edges, size_t count, double total, mst_result_t** out) {
	mst_result_t* r = malloc(sizeof(mst_result_t));
	if (!r) {
		free(edges);
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	r->edges = edges;
	r->edge_count = count;
	r->total_cost = total;
	*out = r;
	return GRAPH_STATUS_OK;
};

static int compare_edge_cost(const void* a, const void* b) {
	double x = ((const edge_t*)a)->construction_cost;
	double y = ((const edge_t*)b)->construction_cost;
	return (x > y) - (x < y);
};

graph_status_t graph_kruskal(const graph_t* graph, mst_result_t** out_result) {
	if (!graph || !out_result) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	graph_status_t s = graph_validate(graph);
	if (s != GRAPH_STATUS_OK) {
		return s;
	};

	size_t n = graph->vertex_count;
	if (n <= 1) {
		return make_mst_result(NULL, 0, 0.0, out_result);
	};

	edge_t* sorted = malloc((graph->edge_count? graph->edge_count : 1) * sizeof(edge_t));
	edge_t* chosen = malloc(n * sizeof(edge_t));
	size_t* parent = malloc(n * sizeof(size_t));
	if (!sorted || !chosen || !parent) {
		free(sorted); free(chosen); free(parent);
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	if (graph->edge_count) {
		memcpy(sorted, graph->edges, graph->edge_count * sizeof(edge_t));
	};

	qsort(sorted, graph->edge_count, sizeof(edge_t), compare_edge_cost);

	/* Union-find clear */
	for (size_t i = 0; i < n; i++) {
		parent[i] = i;
	};

	size_t count = 0;
	double total = 0.0;
	for (size_t i = 0; i < graph->edge_count && count < n - 1; i++) {
		const size_t a = find_vertex_index(graph, sorted[i].source);
		const size_t b = find_vertex_index(graph, sorted[i].target);
		if (dsu_union(parent, a, b)) {
			chosen[count++] = sorted[i];
			total += sorted[i].construction_cost;
		};
	};

	free(sorted);
	free(parent);

	if (count != n - 1) {
		free(chosen);
		return GRAPH_STATUS_DISCONNECTED;
	};

	return make_mst_result(chosen, count, total, out_result);
};

graph_status_t graph_prim(const graph_t* graph, int source_id, mst_result_t** out_result) {
	if (!graph || !out_result) {
		return GRAPH_STATUS_INVALID_ARGUMENT;
	};

	graph_status_t s = graph_validate(graph);
	if (s != GRAPH_STATUS_OK) {
		return s;
	};

	size_t n = graph->vertex_count;
	if (n <= 1) {
		return make_mst_result(NULL, 0, 0.0, out_result);
	};

	edge_t* chosen = malloc(n * sizeof(edge_t));
	bool* in_tree = calloc(n, sizeof(bool));
	if (!chosen || !in_tree) {
		free(chosen); free(in_tree);
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	// 2. Buscar el índice del source_id en lugar de hardcodear el 0
	size_t start_idx = find_vertex_index(graph, source_id);
	if (start_idx == NOT_FOUND) {
		free(chosen);
		free(in_tree);
		return GRAPH_STATUS_VERTEX_NOT_FOUND;
	};

	in_tree[start_idx] = true; // <--- Se inicia la raíz en la zona seleccionada

	size_t count = 0;
	double total = 0.0;
	while (count < n - 1) {
		size_t best = NOT_FOUND, best_new = 0;

		for (size_t i = 0; i < graph->edge_count; i++) {
			const edge_t* e = &graph->edges[i];
			size_t a = find_vertex_index(graph, e->source);
			size_t b = find_vertex_index(graph, e->target);
			if (in_tree[a] == in_tree[b]) {
				continue;
			};

			if (best == NOT_FOUND || e->construction_cost < graph->edges[best].construction_cost) {
				best = i;
				best_new = in_tree[a] ? b : a;
			};
		};

		if (best == NOT_FOUND) {
			free(chosen);
			free(in_tree);
			return GRAPH_STATUS_DISCONNECTED;
		};

		in_tree[best_new] = true;
		chosen[count++] = graph->edges[best];
		total += graph->edges[best].construction_cost;
	};

	free(in_tree);
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
	if (!result) return;
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

static void residual_free(residual_t* r) {
	free(r->to);
	free(r->next);
	free(r->head);
	free(r->cap);
};

static bool residual_init(residual_t* r, size_t nodes, size_t arcs) {
	r->node_count = nodes;
	r->arc_count = 0;
	r->to = malloc(arcs * sizeof(size_t));
	r->next = malloc(arcs * sizeof(size_t));
	r->head = malloc(nodes * sizeof(size_t));
	r->cap = malloc(arcs * sizeof(double));
	if (!r->to || !r->next || !r->head || !r->cap) {
		residual_free(r);
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

	const graph_status_t st = graph_validate(graph);
	if (st != GRAPH_STATUS_OK) {
		return st;
	};

	const size_t n = graph->vertex_count;
	const size_t m = graph->edge_count;
	const size_t src = find_vertex_index(graph, source);
	if (src == NOT_FOUND) {
		return GRAPH_STATUS_VERTEX_NOT_FOUND;
	};

	if (m != n - 1 || !graph_is_connected(graph)) {
		return GRAPH_STATUS_INVALID_GRAPH;
	};

	/* Validate demands. */
	for (size_t i = 0; i < demand_count; i++) {
		if (!valid_weight(demands[i].demand)) {
			return GRAPH_STATUS_INVALID_ARGUMENT;
		};

		if (demands[i].vertex_id == source) {
			return GRAPH_STATUS_INVALID_ARGUMENT;
		};

		if (find_vertex_index(graph, demands[i].vertex_id) == NOT_FOUND) {
			return GRAPH_STATUS_VERTEX_NOT_FOUND;
		};

		for (size_t j = i + 1; j < demand_count; j++) {
			if (demands[i].vertex_id == demands[j].vertex_id) {
				return GRAPH_STATUS_INVALID_ARGUMENT;
			};
		};
	};

	/* Build the residual network. Node n is the artificial sink. */
	size_t sink = n;
	residual_t r;
	if (!residual_init(&r, n + 1, 2 * m + 2 * demand_count + 1)) {
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	for (size_t k = 0; k < m; k++) {
		const size_t a = find_vertex_index(graph, graph->edges[k].source);
		const size_t b = find_vertex_index(graph, graph->edges[k].target);
		residual_add_arc(&r, a, b, graph->edges[k].capacity);
		residual_add_arc(&r, b, a, graph->edges[k].capacity);
	};

	size_t sink_arc_base = r.arc_count;
	for (size_t i = 0; i < demand_count; i++) {
		const size_t v = find_vertex_index(graph, demands[i].vertex_id);
		residual_add_arc(&r, v, sink, demands[i].demand);
		residual_add_arc(&r, sink, v, 0.0);
	};

	size_t* parent_arc = malloc((n + 1) * sizeof(size_t));
	bool* visited = malloc((n + 1) * sizeof(bool));
	size_t* list = malloc((n + 1) * sizeof(size_t));
	flow_result_t* res = calloc(1, sizeof(flow_result_t));
	size_t edge_alloc = m ? m : 1, vertex_alloc = demand_count ? demand_count : 1;
	edge_flow_t* edge_flows = malloc(edge_alloc * sizeof(edge_flow_t));
	vertex_flow_t* vertex_flows = malloc(vertex_alloc * sizeof(vertex_flow_t));
	if (!parent_arc || !visited || !list || !res || !edge_flows || !vertex_flows) {
		free(parent_arc);
		free(visited);
		free(list);
		free(res);
		free(edge_flows);
		free(vertex_flows);
		residual_free(&r);
		return GRAPH_STATUS_OUT_OF_MEMORY;
	};

	while (find_augmenting_path(&r, src, sink, bfs, parent_arc, visited, list) > 0.0) {
		/* keep augmenting */
	};

	for (size_t k = 0; k < m; k++) {
		const edge_t* e = &graph->edges[k];
		double flow = fabs(e->capacity - r.cap[2 * k]);
		if (flow > e->capacity) {
			flow = e->capacity;
		};

		edge_flow_t* ef = &edge_flows[k];
		ef->source = e->source;
		ef->target = e->target;
		ef->capacity = e->capacity;
		ef->flow = flow;
		ef->residual_capacity = e->capacity - flow;
		ef->utilization = e->capacity > 0.0 ? flow / e->capacity : 0.0;
		ef->saturated = ef->residual_capacity <= FLOW_EPS;
	};

	double total_flow = 0.0, total_demand = 0.0;
	for (size_t i = 0; i < demand_count; i++) {
		double delivered = demands[i].demand - r.cap[sink_arc_base + 2 * i];
		if (delivered < 0.0) {
			delivered = 0.0;
		};

		vertex_flow_t* vf = &vertex_flows[i];
		vf->vertex_id = demands[i].vertex_id;
		vf->demand = demands[i].demand;
		vf->delivered = delivered;
		vf->unmet = demands[i].demand - delivered;
		total_flow += delivered;
		total_demand += demands[i].demand;
	};

	res->total_flow = total_flow;
	res->total_demand = total_demand;
	res->edge_flows = edge_flows;
	res->edge_flow_count = m;
	res->vertex_flows = vertex_flows;
	res->vertex_flow_count = demand_count;
	*out_result = res;

	free(parent_arc);
	free(visited);
	free(list);
	residual_free(&r);
	return GRAPH_STATUS_OK;
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
