"""Exercise the closed FHCP format, error precedence and reader ownership."""

from io import BytesIO, StringIO

import pytest

from src.graphs import (
    Graph, GraphError, ReaderError, check_route_legality,
    read_hcp, read_tour, route_to_internal,
)


HCP_HEADER = ["TYPE : HCP", "DIMENSION : 3", "EDGE_DATA_FORMAT : EDGE_LIST"]
TOUR_HEADER = ["TYPE : TOUR", "DIMENSION : 3"]
TRIANGLE_EDGES = ["1 2", "2 3", "3 1"]


def encoded(lines, newline=b"\n", final=True):
    return newline.join(line.encode("ascii") for line in lines) + (newline if final else b"")


def hcp_bytes(edges=TRIANGLE_EDGES, header=HCP_HEADER):
    return encoded([*header, "EDGE_DATA_SECTION", *edges, "-1", "EOF"])


def tour_bytes(labels=(1, 2, 3), header=TOUR_HEADER):
    return encoded([*header, "TOUR_SECTION", *map(str, labels), "-1", "EOF"])


@pytest.fixture
def triangle():
    return Graph([1, 2, 3], [(1, 2), (2, 3), (3, 1)])


@pytest.mark.parametrize("kind", ["HCP", "TOUR"])
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
@pytest.mark.parametrize("final", [False, True])
def test_valid_files_and_explicit_conversion(tmp_path, triangle, kind, newline, final):
    if kind == "HCP":
        lines = ["COMMENT:", "DIMENSION:3", "NAME : triangle", "EDGE_DATA_FORMAT: EDGE_LIST",
                 "TYPE:HCP", "EDGE_DATA_SECTION", "3\t1", "2 3", "1 2", "-1", "EOF"]
    else:
        lines = ["COMMENT:", "DIMENSION:3", "NAME:", "TYPE:TOUR", "TOUR_SECTION",
                 "3", "1", "2", "-1", "EOF"]
    path = tmp_path / "input"
    path.write_bytes(encoded(lines, newline, final))
    if kind == "HCP":
        graph = read_hcp(path)
        assert graph.vertex_count() == 3
        assert graph.edge_count() == 3
        assert list(graph.edges()) == [(0, 1), (0, 2), (1, 2)]
        assert graph.neighbors(0).tolist() == [1, 2]
        assert graph.has_edge(2, 0) and graph.has_edge(0, 2)
        assert tuple(graph.external_label(i) for i in range(3)) == (1, 2, 3)
        assert dict(graph.source) == {"name": "triangle", "comment": ""}
    else:
        labels = read_tour(path, triangle)
        assert labels == (3, 1, 2)
        assert route_to_internal(triangle, labels) == (2, 0, 1)


@pytest.mark.parametrize("dimension,edges,degrees", [
    (1, [], [0]), (2, [], [0, 0]), (2, ["2 1"], [1, 1]),
    (3, ["1 3"], [1, 0, 1]), (3, [], [0, 0, 0]),
])
def test_universe_includes_isolated_vertices(dimension, edges, degrees):
    header = ["TYPE:HCP", f"DIMENSION:{dimension}", "EDGE_DATA_FORMAT:EDGE_LIST"]
    graph = read_hcp(BytesIO(hcp_bytes(edges, header)))
    assert graph.vertex_count() == dimension
    assert graph.edge_count() == len(edges)
    assert [graph.degree(i) for i in range(dimension)] == degrees
    assert [graph.external_label(i) for i in range(dimension)] == list(range(1, dimension + 1))


def test_edge_order_and_orientation_do_not_change_the_graph():
    for edges in [TRIANGLE_EDGES, ["1 3", "3 2", "2 1"], ["3 1", "1 2", "2 3"]]:
        graph = read_hcp(BytesIO(hcp_bytes(edges)))
        assert list(graph.edges()) == [(0, 1), (0, 2), (1, 2)]


# Every row and listed variant of #17's invalid-input table is represented.
HCP_INVALID = [
    (b"NAME : gr\xc3\xa1fica\n", "invalid_encoding", 1),
    (b"NAME triangle\n", "malformed_header", 1),
    (b"NAME broken_SECTION\n", "malformed_header", 1),
    (encoded([*HCP_HEADER, "NAME broken_SECTION", "EDGE_DATA_SECTION"]), "malformed_header", 4),
    (b"\n", "malformed_header", 1),
    (b"CAPACITY : 5\n", "unknown_keyword", 1),
    (b"NAME:a\nNAME:b\n", "repeated_keyword", 2),
    (encoded(["DIMENSION:3", "EDGE_DATA_FORMAT:EDGE_LIST", "EDGE_DATA_SECTION"]), "missing_keyword", 3),
    (encoded(["TYPE:HCP", "EDGE_DATA_FORMAT:EDGE_LIST", "EDGE_DATA_SECTION"]), "missing_keyword", 3),
    (encoded(["TYPE:HCP", "DIMENSION:3", "EDGE_DATA_SECTION"]), "missing_keyword", 3),
    (encoded(HCP_HEADER), "missing_section", 4),
    (hcp_bytes(header=["TYPE:TSP", *HCP_HEADER[1:]]), "unsupported_type", 1),
    (hcp_bytes(header=["TYPE:TOUR", *HCP_HEADER[1:]]), "unsupported_type", 1),
    (hcp_bytes(header=[*HCP_HEADER[:2], "EDGE_DATA_FORMAT:ADJ_LIST"]), "unsupported_edge_format", 3),
    *[(hcp_bytes(header=["TYPE:HCP", f"DIMENSION:{value}", HCP_HEADER[2]]), "invalid_dimension", 2)
      for value in ("0", "-3", "3.0")],
    *[(hcp_bytes([value]), "malformed_edge_line", 5) for value in ("1 2 3", "1 x", "01 2", "")],
    (hcp_bytes(["1 4"]), "unknown_label", 5),
    (hcp_bytes(["2 2"]), "self_loop", 5),
    *[(hcp_bytes(["1 2", value]), "duplicate_edge", 6) for value in ("1 2", "2 1")],
    (encoded([*HCP_HEADER, "EDGE_DATA_SECTION", "1 2"]), "missing_terminator", 6),
    (encoded([*HCP_HEADER, "EDGE_DATA_SECTION", "1 2", "EOF"]), "missing_terminator", 6),
    (encoded([*HCP_HEADER, "EDGE_DATA_SECTION", "-1"]), "missing_eof", 6),
    (hcp_bytes() + b"extra\n", "trailing_content", 10),
    (encoded([*HCP_HEADER, "EDGE_DATA_SECTION", "-1", "-1", "EOF"]), "trailing_content", 6),
    (encoded([*HCP_HEADER, "EDGE_DATA_SECTION", "-1", "extra", "EOF"]), "trailing_content", 6),
]


@pytest.mark.parametrize("payload,code,line", HCP_INVALID)
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_hcp_contract_rejections(payload, code, line, newline):
    with pytest.raises(ReaderError) as error:
        read_hcp(BytesIO(payload.replace(b"\n", newline)))
    assert isinstance(error.value, GraphError)
    assert error.value.code == code
    assert error.value.line == line
    assert error.value.detail
    assert f"line {line}" in str(error.value)


TOUR_INVALID = [
    (b"COMMENT:\xff\n", "invalid_encoding", 1),
    (b"TYPE TOUR\n", "malformed_header", 1),
    (encoded([*TOUR_HEADER, "NAME broken_SECTION", "TOUR_SECTION"]), "malformed_header", 3),
    (b"\n", "malformed_header", 1),
    (b"EDGE_DATA_FORMAT:EDGE_LIST\n", "unknown_keyword", 1),
    (b"NAME:a\nNAME:a\n", "repeated_keyword", 2),
    (encoded(["DIMENSION:3", "TOUR_SECTION"]), "missing_keyword", 2),
    (encoded(["TYPE:TOUR", "TOUR_SECTION"]), "missing_keyword", 2),
    (encoded(TOUR_HEADER), "missing_section", 3),
    (tour_bytes(header=["TYPE:HCP", "DIMENSION:3"]), "unsupported_type", 1),
    *[(tour_bytes(header=["TYPE:TOUR", f"DIMENSION:{value}"]), "invalid_dimension", 2)
      for value in ("0", "-3", "3.0")],
    (tour_bytes(header=["TYPE:TOUR", "DIMENSION:4"]), "dimension_mismatch", 2),
    *[(tour_bytes([value]), "malformed_tour_line", 4) for value in ("1 2", "x", "01", "0", "+1", "")],
    (encoded([*TOUR_HEADER, "TOUR_SECTION", "1"]), "missing_terminator", 5),
    (encoded([*TOUR_HEADER, "TOUR_SECTION", "EOF"]), "missing_terminator", 4),
    (encoded([*TOUR_HEADER, "TOUR_SECTION", "-1"]), "missing_eof", 5),
    (tour_bytes() + b"extra\n", "trailing_content", 9),
    (encoded([*TOUR_HEADER, "TOUR_SECTION", "-1", "-1", "EOF"]), "trailing_content", 5),
    (encoded([*TOUR_HEADER, "TOUR_SECTION", "-1", "", "EOF"]), "trailing_content", 5),
]


@pytest.mark.parametrize("payload,code,line", TOUR_INVALID)
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_tour_contract_rejections(triangle, payload, code, line, newline):
    with pytest.raises(ReaderError) as error:
        read_tour(BytesIO(payload.replace(b"\n", newline)), triangle)
    assert error.value.code == code
    assert error.value.line == line
    assert error.value.detail


@pytest.mark.parametrize("labels", [(), (1,), (1, 2, 3, 1), (1, 1, 2), (1, 2, 4), (2**80, 1, 3)])
def test_tour_does_not_convert_repair_or_certify(triangle, labels):
    result = read_tour(BytesIO(tour_bytes(labels)), triangle)
    assert result == labels
    if 4 in labels or 2**80 in labels:
        with pytest.raises(GraphError, match="unknown_label"):
            route_to_internal(triangle, result)
    else:
        route = route_to_internal(triangle, result)
        assert not check_route_legality(3, route).valid


@pytest.mark.parametrize("payload,code,line", [
    (b"BROKEN\n\xff\n", "malformed_header", 1),
    (b"TYPE:TSP\nNAME:a\nNAME:b\n", "repeated_keyword", 3),
    (b"TYPE:TSP\nTOUR_SECTION\n", "missing_keyword", 2),
    (encoded(["TYPE:TSP", "DIMENSION:0", "EDGE_DATA_FORMAT:ADJ_LIST", "TOUR_SECTION"]), "missing_section", 4),
    (hcp_bytes(header=["TYPE:TSP", "DIMENSION:0", "EDGE_DATA_FORMAT:ADJ_LIST"]), "unsupported_type", 1),
    (hcp_bytes(header=["TYPE:HCP", "DIMENSION:0", "EDGE_DATA_FORMAT:ADJ_LIST"]), "unsupported_edge_format", 3),
    (hcp_bytes(["4 4"]), "unknown_label", 5),
    (hcp_bytes(["2 2", "2 2"]), "self_loop", 5),
    (encoded([*HCP_HEADER, "EDGE_DATA_SECTION", "1 x"]) + b"\xff\n", "malformed_edge_line", 5),
    (encoded([*HCP_HEADER, "EDGE_DATA_SECTION", "1 4"]) + b"\xff\n", "unknown_label", 5),
])
def test_first_error_precedence(payload, code, line):
    with pytest.raises(ReaderError) as error:
        read_hcp(BytesIO(payload))
    assert (error.value.code, error.value.line) == (code, line)


@pytest.mark.parametrize("payload,code,line", [
    (b"", "missing_keyword", 1),
    (encoded(HCP_HEADER, final=False), "missing_section", 4),
    (encoded([*HCP_HEADER, "EDGE_DATA_SECTION"], final=False), "missing_terminator", 5),
    (encoded([*HCP_HEADER, "EDGE_DATA_SECTION", "-1"], final=False), "missing_eof", 6),
    (b"TYPE:HCP\rDIMENSION:3\r", "malformed_header", 1),
    (b"type:HCP\n", "unknown_keyword", 1),
    (hcp_bytes(["+1 2"]), "malformed_edge_line", 5),
    (hcp_bytes(["0 2"]), "malformed_edge_line", 5),
    (hcp_bytes(["1\v2"]), "malformed_edge_line", 5),
    (hcp_bytes(["1\r 2"]), "malformed_edge_line", 5),
])
def test_additional_closed_profile_and_eof_cases(payload, code, line):
    with pytest.raises(ReaderError) as error:
        read_hcp(BytesIO(payload))
    assert (error.value.code, error.value.line) == (code, line)


@pytest.mark.parametrize("kind", ["HCP", "TOUR"])
def test_blank_lines_after_eof_are_allowed(triangle, kind):
    if kind == "HCP":
        assert read_hcp(BytesIO(hcp_bytes() + b"\n \t\r\n")).edge_count() == 3
    else:
        assert read_tour(BytesIO(tour_bytes() + b"\n \t\r\n"), triangle) == (1, 2, 3)


def test_source_is_copied_with_descriptive_headers_taking_precedence():
    source = {"instance_id": "synthetic", "sha256": "unverified", "name": "caller", "comment": "caller"}
    payload = hcp_bytes(header=["NAME:file", "COMMENT:", *HCP_HEADER])
    graph = read_hcp(BytesIO(payload), source=source)
    assert dict(graph.source) == {"instance_id": "synthetic", "sha256": "unverified", "name": "file", "comment": ""}
    source["instance_id"] = "changed"
    assert graph.source["instance_id"] == "synthetic"
    assert read_hcp(BytesIO(hcp_bytes()), source={"name": "caller"}).source["name"] == "caller"
    assert dict(read_hcp(BytesIO(hcp_bytes())).source) == {}
    with pytest.raises(TypeError):
        read_hcp(BytesIO(payload), source={"name": []})


def test_descriptive_values_can_contain_colons_and_section_names():
    graph = read_hcp(BytesIO(hcp_bytes(header=[
        "COMMENT:http://example.test/TOUR_SECTION", "NAME:EDGE_DATA_SECTION", *HCP_HEADER,
    ])))
    assert graph.source["comment"] == "http://example.test/TOUR_SECTION"
    assert graph.source["name"] == "EDGE_DATA_SECTION"


@pytest.mark.parametrize("kind", ["HCP", "TOUR"])
@pytest.mark.parametrize("invalid", [False, True])
def test_caller_streams_remain_open_at_current_position(triangle, kind, invalid):
    payload = (b"BROKEN\n" if invalid else hcp_bytes() if kind == "HCP" else tour_bytes())
    stream = BytesIO(b"prefix\n" + payload)
    stream.seek(len(b"prefix\n"))
    read = (lambda file: read_hcp(file)) if kind == "HCP" else (lambda file: read_tour(file, triangle))
    if invalid:
        with pytest.raises(ReaderError) as error:
            read(stream)
        assert error.value.line == 1
    else:
        read(stream)
        assert stream.read() == b""
    assert not stream.closed


@pytest.mark.parametrize("kind", ["HCP", "TOUR"])
@pytest.mark.parametrize("invalid", [False, True])
def test_owned_files_close_on_success_and_failure(tmp_path, monkeypatch, triangle, kind, invalid):
    path = tmp_path / "input"
    path.write_bytes(b"BROKEN\n" if invalid else hcp_bytes() if kind == "HCP" else tour_bytes())
    opened = []
    builtin_open = open

    def record_open(*args, **kwargs):
        stream = builtin_open(*args, **kwargs)
        opened.append(stream)
        return stream

    monkeypatch.setattr("builtins.open", record_open)
    read = (lambda file: read_hcp(file)) if kind == "HCP" else (lambda file: read_tour(file, triangle))
    if invalid:
        with pytest.raises(ReaderError):
            read(str(path))
    else:
        read(str(path))
    assert len(opened) == 1 and opened[0].closed


def test_nonseekable_binary_stream():
    class ForwardOnly:
        def __init__(self, payload):
            self.stream = BytesIO(payload)

        def readline(self):
            return self.stream.readline()

    assert read_hcp(ForwardOnly(hcp_bytes())).vertex_count() == 3


def test_io_and_python_argument_errors_are_not_format_errors(tmp_path, triangle):
    with pytest.raises(FileNotFoundError):
        read_hcp(tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        read_tour(tmp_path / "missing", triangle)
    with pytest.raises(TypeError, match="binary"):
        read_hcp(StringIO("TYPE:HCP\n"))


def test_csr_capacity_is_checked_before_allocating_vertices():
    with pytest.raises(OverflowError, match="int32"):
        read_hcp(BytesIO(hcp_bytes(header=["TYPE:HCP", f"DIMENSION:{2**31}", HCP_HEADER[2]])))
