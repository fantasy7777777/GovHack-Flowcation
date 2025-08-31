import osmnx as ox, networkx as nx
import matplotlib.pyplot as plt
from shapely.geometry import Point
import geopandas as gpd
import pandas as pd



# ----------------------------
# Graph Setup
# ----------------------------
def graph_init(places, traffic_geojson, volume_csv):
    """Initialise graph, speeds, travel times, and inject delays."""

    ox.settings.cache_folder = "cache_walk"

    G = ox.graph_from_place(places, network_type="walk")

    nx.set_edge_attributes(G, 5, "speed_kph")
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
            delay = 30
        else:
            delay = 5  # unsignalised default

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

    hull = gdf_proj.buffer(150).union_all().convex_hull
    if hull.is_empty:
        return reachable_nodes, gpd.GeoDataFrame(geometry=[])

    hull_gdf = gpd.GeoDataFrame(geometry=[hull], crs=gdf_proj.crs).to_crs(epsg=4326)
    return reachable_nodes, hull_gdf


# ----------------------------
# Multi-Plot
# ----------------------------
def plot_all_rings(G, features, cutoff=20*60):
    """Plot all school rings on one map."""
    edge_colors = []
    for u, v, k, data in G.edges(keys=True, data=True):
        if data.get("highway") in ["cycleway", "path", "track"]:
            edge_colors.append("maroon")   # cycle-dedicated
        else:
            edge_colors.append("dimgray") 

    fig, ax = ox.plot_graph(
        G,
        bgcolor="lightgrey",
        node_size=0,
        node_color="lightgrey",
        edge_color=edge_colors,
        edge_linewidth=0.5,
        show=False,
        close=False,
    )

    # --- get polygons ---
    # Buildings
    buildings = ox.features_from_place(places, tags={"building": True})
    # Parks/green space
    parks = ox.features_from_place(places, tags={"leisure": "park"})
    # Water (rivers, lakes)
    water = ox.features_from_place(places, tags={"natural": "water"})
    #filter for polygons
    parks = parks[parks.geom_type.isin(["Polygon", "MultiPolygon"])]
    water = water[water.geom_type.isin(["Polygon", "MultiPolygon"])]
    buildings = buildings[buildings.geom_type.isin(["Polygon", "MultiPolygon"])]

    suburbs = ox.features_from_place(
    "City of Melbourne, Victoria, Australia",
    tags={"place": "suburb"}
    )
    suburbs = suburbs[suburbs.geom_type.isin(["Polygon", "MultiPolygon"])]
    for idx, row in suburbs.iterrows():
        centroid = row.geometry.centroid
        ax.annotate(
            text=row["name"], 
            xy=(centroid.x, centroid.y),
            fontsize=8,
            ha="center"
        )

    # --- plot polygons ---
    if not buildings.empty:
        buildings.plot(ax=ax, facecolor="grey", edgecolor="none", alpha=0.6, zorder=0)
    if not parks.empty:
        parks.plot(ax=ax, facecolor="green", edgecolor="none", alpha=0.5, zorder=0)
    if not water.empty:
        water.plot(ax=ax, facecolor="blue", edgecolor="none", alpha=0.5, zorder=0)

    # loop over features
    for idx, row in features.iterrows():
        centroid = row.geometry.centroid
        lon, lat = centroid.x, centroid.y
        node = ox.distance.nearest_nodes(G, lon, lat)

        reachable_nodes, hull_gdf = generate_ring(G, node, cutoff=cutoff)

        # hull outline
        if not hull_gdf.empty and hull_gdf.iloc[0].geometry.geom_type == "Polygon":
            hull_gdf.plot(
                ax=ax,
                facecolor="blue",   # fill color
                edgecolor="darkblue",
                alpha=0.10,         # transparency (0=fully transparent, 1=solid)
                linewidth=1.5,
                zorder=3
            )
        # school marker
        ax.scatter(
            lon, lat,
            c="red", s=20,
            edgecolors="white", linewidth=0.8,
            zorder=5
        )

    plt.savefig("Saved_Plots/walk_schools_peak_map.png", dpi=300, bbox_inches="tight")
    plt.show()


places = ["City of Melbourne, Victoria, Australia"]

# 1. Build graph with traffic delays
G = graph_init(places, "Traffic_Lights.geojson", "Traffic_Volumes_Summary.csv")

# 2. Get schools (could later swap for hospitals, shops, etc.)
schools = ox.features_from_place(places, {"amenity": "school", "isced:level": "1"})
schools =schools[schools["name"].str.contains("Primary", case=False, na=False)] # filter for primary
schools = schools.to_crs(epsg=32755)
schools["geometry"] = schools.centroid.to_crs(epsg=4326)

# 3. Plot all schools + all their 20min rings
plot_all_rings(G, schools, cutoff=10*60)


