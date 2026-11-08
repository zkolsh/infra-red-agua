#if !defined(GRAPH_ENGINE_H)
#define GRAPH_ENGINE_H

#include "arena.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef uint32_t vertex_id_t;

typedef uint32_t graph_status_t; enum {
	GRAPH_STATUS_OK = 0,
	GRAPH_STATUS_INVALID_ARGUMENT,
	GRAPH_STATUS_OUT_OF_MEMORY,
	GRAPH_STATUS_VERTEX_NOT_FOUND,
	GRAPH_STATUS_EDGE_NOT_FOUND,
	GRAPH_STATUS_EDGE_ALREADY_EXISTS,
	GRAPH_STATUS_INVALID_GRAPH,
	GRAPH_STATUS_DISCONNECTED,
	GRAPH_STATUS_INVALID_RESULT,
};

typedef struct {
	vertex_id_t id;
} vertex_t;

typedef struct {
	vertex_id_t source;
	vertex_id_t target;

	double construction_cost;
	double capacity;
} edge_t;

typedef struct {
	vertex_t* vertices;
	size_t vertex_count;
	size_t vertex_capacity;

	edge_t* edges;
	size_t edge_count;
	size_t edge_capacity;

	arena_t* arena;
} graph_t;

typedef struct {
	edge_t* edges;
	size_t edge_count;

	double total_cost;
} mst_result_t;

typedef struct {
	vertex_id_t vertex_id;
	double demand;
} vertex_demand_t;

typedef struct {
	vertex_id_t source;
	vertex_id_t target;

	double capacity;
	double flow;
	double residual_capacity;
	double utilization;

	bool saturated;
} edge_flow_t;

typedef struct {
	vertex_id_t vertex_id;

	double demand;
	double delivered;
	double unmet;
} vertex_flow_t;

typedef struct {
	double total_flow;
	double total_demand;

	edge_flow_t* edge_flows;
	size_t edge_flow_count;

	vertex_flow_t* vertex_flows;
	size_t vertex_flow_count;
} flow_result_t;

/* Creates an empty graph. */
graph_t* graph_empty(void);

/* Creates an empty graph with preallocated vertex and edge storage. */
graph_t* graph_init_capacity(size_t vertex_capacity, size_t edge_capacity);

/* Frees all graph memory, including the graph itself.
 * Accepts NULL. */
void graph_deinit(graph_t* graph);

/* Adds a vertex. Vertex IDs must be unique. */
graph_status_t graph_add_vertex(graph_t* graph, vertex_id_t id);

/* Adds an undirected edge between two existing vertices.
 * Construction cost and capacity must be non-negative.
 * Self-loops and duplicate edges are rejected. */
graph_status_t graph_add_edge(graph_t* graph, vertex_id_t source, vertex_id_t target, double construction_cost, double capacity);

/* Replaces the properties of an existing edge.
 * Does not create an edge if it does not exist. */
graph_status_t graph_set_edge(graph_t* graph, vertex_id_t source, vertex_id_t target, double construction_cost, double capacity);

/* Removes an existing undirected edge. */
graph_status_t graph_remove_edge(graph_t* graph, vertex_id_t source, vertex_id_t target);

size_t graph_get_vertex_count(const graph_t* graph);
size_t graph_get_edge_count(const graph_t* graph);
graph_status_t graph_get_vertex_by_id(const graph_t* graph, vertex_id_t id, vertex_t* out_vertex);

/* Endpoint order does not matter. */
graph_status_t graph_get_edge(const graph_t* graph, vertex_id_t source, vertex_id_t target, edge_t* out_edge);

/* Copies vertices into a caller-provided buffer.
 *
 * Returns the number of vertices copied.
 * Copies at most capacity elements. */
size_t graph_get_vertices(const graph_t* graph, vertex_t* out_vertices, size_t capacity);

/* Copies edges into a caller-provided buffer.
 *
 * Returns the number of edges copied.
 * Copies at most capacity elements. */
size_t graph_get_edges(const graph_t* graph, edge_t* out_edges, size_t capacity);

/* Validates graph structure and edge references.
 *
 * Checks:
 * - Valid storage and counts.
 * - Unique vertex IDs.
 * - Valid edge endpoints.
 * - No self-loops or duplicate edges.
 * - Non-negative costs and capacities.
 */
graph_status_t graph_validate(const graph_t* graph);

/* An empty graph is considered connected. */
bool graph_is_connected(const graph_t* graph);

graph_status_t graph_subgraph_from_edges(const graph_t* original, const edge_t* edges, size_t edge_count, graph_t** out_graph);

/* Calculates a minimum spanning tree using Kruskal.
 *
 * Edge construction_cost is the optimization weight.
 * Edge capacity is preserved in the result.
 *
 * Returns GRAPH_STATUS_DISCONNECTED if no spanning tree exists.
 *
 * On success, out_result receives an allocated result. */
graph_status_t graph_kruskal(const graph_t* graph, mst_result_t** out_result);

/* Calculates a minimum spanning tree using Prim.
 *
 * Edge construction_cost is the optimization weight.
 * Edge capacity is preserved in the result.
 *
 * Returns GRAPH_STATUS_DISCONNECTED if no spanning tree exists. */
graph_status_t graph_prim(const graph_t* graph, int source_id, mst_result_t** out_result);

double mst_get_total_cost(const mst_result_t* result);
size_t mst_get_edge_count(const mst_result_t* result);

/* Copies selected edges into a caller-provided buffer.
 * Returns the number of edges copied. */
size_t mst_get_edges(const mst_result_t* result, edge_t* out_edges, size_t capacity);

/* Frees an MST result and its associated memory. Accepts NULL. */
void mst_deinit(mst_result_t* result);

/* Calculates maximum flow using Ford-Fulkerson.
 *
 * graph must represent the selected network as a tree
 * rooted at source.
 *
 * The tree is interpreted as an outward-directed network:
 * water travels from source towards the demand vertices.
 *
 * Each physical edge has one shared capacity.
 *
 * demand_vertices contains the demand of each destination
 * vertex. The source must not appear in this array.
 *
 * Internally, an artificial sink is used to aggregate
 * the demand of all destination vertices.
 *
 * On success, out_result receives an allocated result. */
graph_status_t graph_ford_fulkerson(const graph_t* graph, vertex_id_t source, const vertex_demand_t* demand_vertices, size_t demand_count, flow_result_t** out_result);

/* Calculates maximum flow using Edmonds-Karp.
 *
 * Uses the same graph and demand semantics as
 * graph_ford_fulkerson(). */
graph_status_t graph_edmonds_karp( const graph_t* graph, vertex_id_t source, const vertex_demand_t* demand_vertices, size_t demand_count, flow_result_t** out_result);

/* Returns total delivered flow. */
double flow_get_total(const flow_result_t* result);

/* Returns total requested demand. */
double flow_get_total_demand(const flow_result_t* result);

/* Returns total unmet demand. */
double flow_get_unmet_demand(const flow_result_t* result);

/* Returns whether all requested demand was satisfied. */
bool flow_is_demand_satisfied(const flow_result_t* result);

/* Returns the number of physical edges in the result. */
size_t flow_get_edge_count(const flow_result_t* result);

/* Copies flow information for physical edges. Returns the number of entries copied. */
size_t flow_get_edge_flows(const flow_result_t* result, edge_flow_t* out_flows, size_t capacity);

/* Returns the number of saturated edges. */
size_t flow_get_saturated_edge_count(const flow_result_t* result);

/* Copies saturated edges into a caller-provided buffer. Returns the number of entries copied. */
size_t flow_get_saturated_edges(const flow_result_t* result, edge_flow_t* out_flows, size_t capacity);

/* Returns the number of vertices with demand information. */
size_t flow_get_vertex_count(const flow_result_t* result);

/* Copies per-vertex demand and delivery information. Returns the number of entries copied. */
size_t flow_get_vertex_flows(const flow_result_t* result, vertex_flow_t* out_flows, size_t capacity);

/* Frees a flow result and its associated memory. Accepts NULL. */
void flow_deinit(flow_result_t* result);

#endif /* GRAPH_ENGINE_H */
