from sapextractor.algo.p2p.tab_processing import eban_processing, ekko_processing, ekpo_processing, rbkp_processing, rseg_processing, ekbe_processing, bkpf_processing
import networkx as nx
import pandas as pd
from dateutil import parser
from sapextractor.utils.usr02 import extract_usr02


def add_edges_to_graph(edges, nodes_connections, G):
    for edge in edges:
        if edge[0] in G.nodes and edge[1] in G.nodes:
            G.add_edge(edge[0], edge[1])
        if not edge[0] in nodes_connections:
            nodes_connections[edge[0]] = {edge[0]}
        if not edge[1] in nodes_connections:
            nodes_connections[edge[1]] = {edge[1]}
        nodes_connections[edge[0]].add(edge[1])
    return nodes_connections, G


def extract_tables_and_graph(con, gjahr=None, min_extr_date=None, mandt="800", bukrs="1000", return_ekko_query=False, extra_els_query=None):
    if extra_els_query is None:
        extra_els_query = {}

    G = nx.DiGraph()
    nodes_types = {}
    nodes_connections = {}
    eban, eban_nodes_types = eban_processing.apply(con, mandt=mandt, bukrs=bukrs, gjahr=gjahr, extra_els_query=extra_els_query)
    for n in eban_nodes_types:
        G.add_node(n)
    nodes_types.update(eban_nodes_types)
    ekko, ekko_nodes_types, ekko_query = ekko_processing.apply(con, mandt=mandt, bukrs=bukrs, gjahr=gjahr, extra_els_query=extra_els_query)
    for n in ekko_nodes_types:
        G.add_node(n)
    nodes_types.update(ekko_nodes_types)
    eban_ekko_connection = ekpo_processing.eban_ekko_connection(con, mandt=mandt, bukrs=bukrs, extra_els_query=extra_els_query)
    nodes_connections, G = add_edges_to_graph(eban_ekko_connection, nodes_connections, G)

    rbkp, rbkp_nodes_types, rbkp_query = rbkp_processing.apply(con, gjahr=gjahr, mandt=mandt, bukrs=bukrs, extra_els_query=extra_els_query)
    for n in rbkp_nodes_types:
        G.add_node(n)
    nodes_types.update(rbkp_nodes_types)
    ekko_rbkp_connections = rseg_processing.apply(con, gjahr=gjahr, mandt=mandt, bukrs=bukrs, extra_els_query=extra_els_query)
    nodes_connections, G = add_edges_to_graph(ekko_rbkp_connections, nodes_connections, G)

    gr, gr_nodes_types = ekbe_processing.goods_receipt(con, gjahr=gjahr, mandt=mandt, bukrs=bukrs, extra_els_query=extra_els_query)
    for n in gr_nodes_types:
        G.add_node(n)
    nodes_types.update(gr_nodes_types)
    gr_ekko_connections = ekbe_processing.goods_receipt_ekko_connection(gr)
    nodes_connections, G = add_edges_to_graph(gr_ekko_connections, nodes_connections, G)

    ir, ir_nodes_types = ekbe_processing.invoice_receipt(con, gjahr=gjahr, mandt=mandt, bukrs=bukrs, extra_els_query=extra_els_query)
    for n in ir_nodes_types:
        G.add_node(n)
    nodes_types.update(ir_nodes_types)
    ir_ekko_connections = ekbe_processing.invoice_receipt_ekko_connection(ir)
    nodes_connections, G = add_edges_to_graph(ir_ekko_connections, nodes_connections, G)

    bkpf_events, bkpf_doc_types, bkpf_connections = bkpf_processing.apply(con, gjahr=gjahr, mandt=mandt, bukrs=bukrs, extra_els_query=extra_els_query)
    for n in bkpf_doc_types:
        G.add_node(n)
    nodes_types.update(bkpf_doc_types)
    nodes_connections, G = add_edges_to_graph(bkpf_connections, nodes_connections, G)

    nodes_connections = pd.DataFrame([{"node": x, "RELATED_DOCUMENTS": list(y)} for x, y in nodes_connections.items()])
    dataframe = pd.concat([eban, ekko, rbkp, gr, ir, bkpf_events])
    if len(dataframe) > 0:
        dataframe = dataframe.sort_values("event_timestamp")
        dataframe = dataframe.merge(nodes_connections, left_on="event_node", right_on="node", suffixes=('', '_r'), how="left")
        if min_extr_date is not None:
            min_extr_date = parser.parse(min_extr_date)
            dataframe = dataframe[dataframe["event_timestamp"] >= min_extr_date]

    dictio_ustyp, dictio_class = extract_usr02.apply(con)
    dataframe["event_USERNAME_USTYP"] = dataframe["event_USERNAME"].map(dictio_ustyp)
    dataframe["event_USERNAME_CLASS"] = dataframe["event_USERNAME"].map(dictio_class)

    if return_ekko_query:
        return dataframe, G, nodes_types, ekko_query, rbkp_query
    return dataframe, G, nodes_types
