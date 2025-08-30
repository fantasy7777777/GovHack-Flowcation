import osmnx as ox, networkx as nx
import matplotlib.pyplot as plt
from shapely.geometry import Point
import geopandas as gpd
import pandas as pd
import matplotlib.colors as mcolors
import random


# ----------------------------
# Graph Setup
# ----------------------------
def graph_init(places, traffic_geojson, volume_csv):
    """Initialise graph, speeds, travel times, and inject delays."""
    G = ox.graph_from_place(places, network_type="drive")

    # Default speeds
    default_speeds = {
        "motorway": 100,
        "trunk": 80,
        "primary": 60,
        "secondary": 50,
        "tertiary": 50,
        "residential": 40,
        "service": 20,
    }
    ox.routing.add_edge_speeds(G, hwy_speeds=default_speeds, fallback=40)
    ox.routing.add_edge_travel_times(G)

    # Load traffic lights + volumes
    traffic_lights = gpd.read_file(traffic_geojson)
    volume_df = pd.read_csv(volume_csv)
    volume_dict = volume_df.set_index("NB_SCATS_SITE")[
        ["offpeak_volume", "peak_volume"]
    ].to_dict("index")

    # Attach delays to nodes
    for _, row in traffic_lights.iterrows():
        lon, lat = row["geometry"].x, row["geometry"].y
        nearest_node = ox.distance.nearest_nodes(G, lon, lat)
        G.nodes[nearest_node]["site_no"] = row["SITE_NO"]

        vols = volume_dict.get(row["SITE_NO"])
        if vols:
            G.nodes[nearest_node]["offpeak_volume"] = vols["offpeak_volume"]
            G.nodes[nearest_node]["peak_volume"] = vols["peak_volume"]
        else:
            G.nodes[nearest_node]["offpeak_volume"] = 0
            G.nodes[nearest_node]["peak_volume"] = 0

    # Apply delays to edges
    for node, data in G.nodes(data=True):
        if "peak_volume" in data and data["peak_volume"] > 0:
            delay = min(120, data["peak_volume"] / 200.0)  # cap at 2 min
        else:
            delay = 10  # unsignalised default

        for u, v, k in G.in_edges(node, keys=True):
            G[u][v][k]["travel_time"] += delay
        for u, v, k in G.out_edges(node, keys=True):
            G[u][v][k]["travel_time"] += delay

    return G


# ----------------------------
# Ring Generator
# ----------------------------
def generate_ring(G, node, cutoff=20*60):
    lengths = nx.single_source_dijkstra_path_length(
        G, node, cutoff=cutoff, weight="travel_time"
    )
    if not lengths:
        return [], gpd.GeoDataFrame(geometry=[])

    reachable_nodes = list(lengths.keys())
    points = [Point((G.nodes[n]["x"], G.nodes[n]["y"])) for n in reachable_nodes]
    gdf = gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")

    gdf_proj = gdf.to_crs(epsg=32755)  # meters
    if gdf_proj.empty:
        return reachable_nodes, gpd.GeoDataFrame(geometry=[])

    hull = gdf_proj.union_all().convex_hull
    if hull.is_empty:
        return reachable_nodes, gpd.GeoDataFrame(geometry=[])

    hull_gdf = gpd.GeoDataFrame(geometry=[hull], crs=gdf_proj.crs).to_crs(epsg=4326)
    return reachable_nodes, hull_gdf


# ----------------------------
# Multi-Plot
# ----------------------------
def plot_all_rings(G, features, cutoff=20*60):
    """Plot all school rings on one map."""
    fig, ax = ox.plot_graph(
        G,
        node_size=1,
        node_color="lightgrey",
        edge_color="grey",
        show=False,
        close=False,
    )

    # loop over features
    for idx, row in features.iterrows():
        centroid = row.geometry.centroid
        lon, lat = centroid.x, centroid.y
        node = ox.distance.nearest_nodes(G, lon, lat)

        reachable_nodes, hull_gdf = generate_ring(G, node, cutoff=cutoff)

        # hull outline
        if not hull_gdf.empty and hull_gdf.iloc[0].geometry.geom_type == "Polygon":
            hull_gdf.boundary.plot(ax=ax, linewidth=2, alpha=0.6)

        # school marker
        ax.scatter(
            lon, lat,
            c="red", s=60,
            edgecolors="white", linewidth=0.8,
            zorder=5
        )

    plt.show()


places = [
    "Parkville, Victoria, Australia",
    "Carlton, Victoria, Australia",
    "Fitzroy, Victoria, Australia",
    "North Melbourne, Victoria, Australia"
]

# 1. Build graph with traffic delays
G = graph_init(places, "Traffic_Lights.geojson", "Traffic_Volumes_Summary.csv")

# 2. Get schools (could later swap for hospitals, shops, etc.)
schools = ox.features_from_place(places, {"amenity": "school"})
schools = schools.to_crs(epsg=4326)  # ensure consistency
schools["geometry"] = schools.centroid

# 3. Plot all schools + all their 20min rings
plot_all_rings(G, schools, cutoff=4*60)
