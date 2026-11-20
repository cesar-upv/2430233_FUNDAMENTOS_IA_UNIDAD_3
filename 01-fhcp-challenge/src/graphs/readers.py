"""Strict readers for the closed FHCP HCP/TOUR profile from contract #17."""

from collections.abc import Iterator, Mapping
from contextlib import nullcontext
from os import PathLike
import re
from typing import BinaryIO

from .graph import Graph, GraphError


type FileInput = str | PathLike[str] | BinaryIO

_LABEL = r"[1-9][0-9]*"
_EDGE = re.compile(rf"({_LABEL})[ \t]+({_LABEL})")
_TOUR_LABEL = re.compile(_LABEL)
_SECTION_MARKER = re.compile(r"[A-Z][A-Z0-9_]*_SECTION")


class ReaderError(GraphError):
    """First format error, with a one-based line relative to the input start."""

    def __init__(self, code: str, line: int, detail: str):
        self.line = line
        super().__init__(code, detail)
        self.args = (f"{code} at line {line}: {detail}",)


def _open_input(file: FileInput):
    # Only streams opened here belong to the reader.
    if isinstance(file, (str, PathLike)):
        return open(file, "rb")
    return nullcontext(file)


class _Reader:
    def __init__(self, stream: BinaryIO):
        self.stream = stream
        self.line = 0

    def next_line(self, malformed_code: str) -> str | None:
        raw = self.stream.readline()
        if not isinstance(raw, bytes):
            raise TypeError("Readers require a binary stream.")
        if not raw:
            return None
        self.line += 1
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError as error:
            raise ReaderError("invalid_encoding", self.line, "Expected ASCII bytes.") from error
        if text.endswith("\n"):
            text = text[:-1]
            if text.endswith("\r"):
                text = text[:-1]
        if "\r" in text:
            raise ReaderError(malformed_code, self.line, "Only LF and CRLF line endings are allowed.")
        return text.strip(" \t")

    def header(self, kind: str, size: int | None = None) -> tuple[int, dict[str, str]]:
        required = ["TYPE", "DIMENSION"]
        if kind == "HCP":
            required.append("EDGE_DATA_FORMAT")
        allowed = {"NAME", "COMMENT", *required}
        expected_section = "EDGE_DATA_SECTION" if kind == "HCP" else "TOUR_SECTION"
        values: dict[str, str] = {}
        positions: dict[str, int] = {}
        section = None
        while True:
            text = self.next_line("malformed_header")
            if text is None or text == "EOF" or _SECTION_MARKER.fullmatch(text):
                section = text
                boundary = self.line + 1 if text is None else self.line
                break
            key, separator, value = text.partition(":")
            if not separator:
                raise ReaderError("malformed_header", self.line, "Expected KEYWORD : value.")
            key, value = key.strip(" \t"), value.strip(" \t")
            if key not in allowed:
                raise ReaderError("unknown_keyword", self.line, f"Unknown keyword: {key!r}.")
            if key in values:
                raise ReaderError("repeated_keyword", self.line, f"Repeated keyword: {key}.")
            values[key] = value
            positions[key] = self.line

        # Contract order: missing keywords, section, type, format, dimension.
        for key in required:
            if key not in values:
                raise ReaderError("missing_keyword", boundary, f"Missing keyword: {key}.")
        if section != expected_section:
            raise ReaderError("missing_section", boundary, f"Expected {expected_section}.")
        if values["TYPE"] != kind:
            raise ReaderError("unsupported_type", positions["TYPE"], f"Expected TYPE : {kind}.")
        if kind == "HCP" and values["EDGE_DATA_FORMAT"] != "EDGE_LIST":
            raise ReaderError(
                "unsupported_edge_format", positions["EDGE_DATA_FORMAT"],
                "Expected EDGE_DATA_FORMAT : EDGE_LIST.",
            )
        try:
            if not re.fullmatch(r"[0-9]+", values["DIMENSION"]):
                raise ValueError
            dimension = int(values["DIMENSION"])
            if dimension < 1:
                raise ValueError
        except ValueError as error:
            raise ReaderError(
                "invalid_dimension", positions["DIMENSION"], "DIMENSION must be a positive decimal integer.",
            ) from error
        if size is not None and dimension != size:
            raise ReaderError(
                "dimension_mismatch", positions["DIMENSION"],
                f"TOUR dimension {dimension} differs from graph size {size}.",
            )
        return dimension, values

    def data_lines(self, malformed_code: str) -> Iterator[str]:
        while True:
            text = self.next_line(malformed_code)
            if text is None or text == "EOF":
                line = self.line + 1 if text is None else self.line
                raise ReaderError("missing_terminator", line, "Expected -1 before EOF.")
            if text == "-1":
                break
            yield text

        text = self.next_line("trailing_content")
        if text is None:
            raise ReaderError("missing_eof", self.line + 1, "Expected EOF after -1.")
        if text != "EOF":
            raise ReaderError("trailing_content", self.line, "Expected EOF immediately after -1.")
        while (text := self.next_line("trailing_content")) is not None:
            if text:
                raise ReaderError("trailing_content", self.line, "Only blank lines may follow EOF.")


def read_hcp(file: FileInput, *, source: Mapping[str, str] | None = None) -> Graph:
    """Read an HCP into CSR, retaining the complete 1..DIMENSION universe.

    Paths are opened in binary mode and closed here; caller streams stay open.
    Optional source metadata is copied; file NAME/COMMENT take precedence.
    No manifest or hash is checked, and no Hamiltonicity is assumed.
    """
    with _open_input(file) as stream:
        reader = _Reader(stream)
        dimension, headers = reader.header("HCP")
        if dimension > 2**31 - 1:
            raise OverflowError("The vertex count exceeds int32 CSR capacity.")
        edges: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        for text in reader.data_lines("malformed_edge_line"):
            match = _EDGE.fullmatch(text)
            if match is None:
                raise ReaderError("malformed_edge_line", reader.line, "Expected two positive decimal labels.")
            try:
                left, right = map(int, match.groups())
            except ValueError as error:
                raise ReaderError("malformed_edge_line", reader.line, "Label exceeds integer conversion limits.") from error
            if left > dimension or right > dimension:
                raise ReaderError("unknown_label", reader.line, f"Edge ({left}, {right}) is outside 1..{dimension}.")
            if left == right:
                raise ReaderError("self_loop", reader.line, f"Self loop at label {left}.")
            edge = (min(left, right), max(left, right))
            if edge in seen:
                raise ReaderError("duplicate_edge", reader.line, f"Repeated undirected edge: {edge}.")
            seen.add(edge)
            edges.append(edge)

    metadata = {} if source is None else dict(source)
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in metadata.items()):
        raise TypeError("Source metadata must map strings to strings.")
    for key in ("NAME", "COMMENT"):
        if key in headers:
            metadata[key.lower()] = headers[key]
    return Graph(range(1, dimension + 1), edges, source=metadata)


def read_tour(file: FileInput, graph: Graph) -> tuple[int, ...]:
    """Read external labels without checking length, membership or uniqueness.

    Conversion with route_to_internal and independent certification are explicit
    consumer operations. Only header DIMENSION is compared with the graph.
    """
    with _open_input(file) as stream:
        reader = _Reader(stream)
        reader.header("TOUR", graph.vertex_count())
        labels: list[int] = []
        for text in reader.data_lines("malformed_tour_line"):
            if _TOUR_LABEL.fullmatch(text) is None:
                raise ReaderError("malformed_tour_line", reader.line, "Expected one positive decimal label.")
            try:
                labels.append(int(text))
            except ValueError as error:
                raise ReaderError("malformed_tour_line", reader.line, "Label exceeds integer conversion limits.") from error
    return tuple(labels)
