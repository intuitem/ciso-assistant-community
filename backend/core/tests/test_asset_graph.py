from core.asset_graph import walk_asset_graph

# child, parent
LINKS = [
    ("app", "process"),
    ("db", "app"),
    ("host", "db"),
    ("app2", "process2"),
    ("db", "app2"),
    ("backup", "host"),
]


def test_chain_is_ancestors_and_descendants_only():
    walk = walk_asset_graph("db", LINKS, mode="chain")
    assert set(walk.order) == {
        "db",
        "app",
        "process",
        "app2",
        "process2",
        "host",
        "backup",
    }
    assert walk.side["process"] == "up"
    assert walk.side["backup"] == "down"
    assert walk.side["db"] == "focus"


def test_chain_skips_siblings():
    walk = walk_asset_graph("app", LINKS, mode="chain")
    assert "app2" not in walk.order
    assert "process2" not in walk.order
    assert walk.omitted == {}


def test_connected_reaches_siblings():
    walk = walk_asset_graph("app", LINKS, mode="connected")
    assert {"app2", "process2", "backup"} <= set(walk.order)
    assert all(side == "any" for side in walk.side.values())


def test_hops_are_shortest_distance():
    walk = walk_asset_graph("process", LINKS, mode="chain")
    assert walk.hops == {"process": 0, "app": 1, "db": 2, "host": 3, "backup": 4}


def test_max_hops_counts_what_lies_beyond():
    walk = walk_asset_graph("process", LINKS, mode="chain", max_hops=2)
    assert set(walk.order) == {"process", "app", "db"}
    assert walk.omitted == {"db": 1}
    assert not walk.truncated


def test_limit_truncates_and_reports_omitted():
    walk = walk_asset_graph("db", LINKS, mode="chain", limit=3)
    assert len(walk.order) == 3
    assert walk.truncated
    assert sum(walk.omitted.values()) > 0


def test_expand_reveals_neighbours_past_the_limit():
    walk = walk_asset_graph("db", LINKS, mode="chain", max_hops=1, expand=["host"])
    assert "backup" in walk.order
    assert "host" not in walk.omitted


def test_expand_ignores_nodes_outside_the_walk():
    walk = walk_asset_graph("app", LINKS, mode="chain", expand=["app2"])
    assert "app2" not in walk.order


def test_edges_are_parent_child_between_included_nodes():
    walk = walk_asset_graph("app", LINKS, mode="chain")
    assert ("process", "app") in walk.edges
    assert ("app", "db") in walk.edges
    assert ("app2", "db") not in walk.edges


def test_chain_counts_co_parents_as_elsewhere():
    walk = walk_asset_graph("app", LINKS, mode="chain")
    assert walk.elsewhere == {"db": 1}
    assert walk.omitted == {}


def test_connected_has_nothing_elsewhere():
    walk = walk_asset_graph("app", LINKS, mode="connected")
    assert walk.elsewhere == {}


def test_reveal_draws_skipped_links_in_their_direction():
    walk = walk_asset_graph("app", LINKS, mode="chain", reveal=["db"])
    assert walk.side["app2"] == "up"
    assert walk.omitted == {"app2": 1}
    assert walk.elsewhere == {}


def test_revealed_nodes_can_be_expanded_further():
    walk = walk_asset_graph("app", LINKS, mode="chain", expand=["app2"], reveal=["db"])
    assert walk.side["process2"] == "up"
    assert walk.omitted == {}
